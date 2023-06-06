"""Checkout views."""
from typing import Optional
from uuid import UUID

from blacksheep import (
    Content,
    FromBytes,
    FromJSON,
    FromQuery,
    HTTPException,
    Response,
    auth,
)
from blacksheep.exceptions import NotFound
from blacksheep.server.openapi.common import ContentInfo, ResponseInfo
from loguru import logger
from oes.registration.app import app
from oes.registration.auth import RequireCart
from oes.registration.database import transaction
from oes.registration.docs import docs, docs_helper
from oes.registration.entities.checkout import CheckoutEntity, CheckoutState
from oes.registration.models.cart import CartData
from oes.registration.models.event import EventConfig
from oes.registration.models.payment import PaymentServiceCheckout
from oes.registration.models.pricing import PricingResult
from oes.registration.payment.base import (
    CheckoutMethod,
    CheckoutStateError,
    ValidationError,
)
from oes.registration.serialization import get_converter
from oes.registration.services.auth import AuthService
from oes.registration.services.cart import CartService, validate_changes_apply
from oes.registration.services.checkout import CheckoutService, apply_checkout_changes
from oes.registration.services.event import EventService
from oes.registration.services.registration import (
    RegistrationService,
    assign_registration_numbers,
)
from oes.registration.util import check_not_found
from oes.registration.views.responses import (
    BodyValidationError,
    CheckoutErrorResponse,
    CreateCheckoutResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession


@auth(RequireCart)
@app.router.get("/carts/{cart_id}/checkout-methods")
@docs_helper(
    response_type=list[CheckoutMethod],
    response_summary="The available checkout methods",
    tags=["Checkout"],
)
async def list_available_checkout_methods(
    cart_id: str,
    cart_service: CartService,
    checkout_service: CheckoutService,
    event_config: EventConfig,
) -> list[CheckoutMethod]:
    """List checkout methods."""
    cart_entity = check_not_found(await cart_service.get_cart(cart_id))
    cart_data = cart_entity.get_cart_data_model()

    event = check_not_found(event_config.get_event(cart_data.event_id))

    # TODO: permissions/check event open/visible?

    # Price cart if unpriced, and ignore empty carts

    if len(cart_data.registrations) == 0:
        return []

    if cart_entity.pricing_result:
        pricing_result = get_converter().structure(
            cart_entity.pricing_result, PricingResult
        )
    else:
        pricing_result = await cart_service.price_cart(cart_data, event)
        cart_entity.set_pricing_result(pricing_result)

    methods = await checkout_service.get_checkout_methods_for_cart(
        cart_data, pricing_result
    )

    return methods


@auth(RequireCart)
@app.router.post("/carts/{cart_id}/checkout")
@docs(
    responses={
        200: ResponseInfo(
            "The created checkout details",
            content=[ContentInfo(CreateCheckoutResponse)],
        ),
        409: ResponseInfo(
            "Info about registrations that are out-of-date",
            content=[ContentInfo(CheckoutErrorResponse)],
        ),
    },
    tags=["Checkout"],
)
async def create_checkout(
    cart_id: str,
    service: FromQuery[str],
    method: FromQuery[str],
    cart_service: CartService,
    checkout_service: CheckoutService,
    registration_service: RegistrationService,
    event_config: EventConfig,
    db: AsyncSession,
    _body: Optional[FromBytes],
) -> Response:
    """Create a checkout for a cart."""
    cart_entity = check_not_found(await cart_service.get_cart(cart_id))
    cart = cart_entity.get_cart_data_model()

    # TODO: permissions

    if not checkout_service.is_service_available(service.value):
        raise NotFound

    event = check_not_found(event_config.get_event(cart.event_id))

    # TODO: check event open/visible

    # make sure the changes can still be applied
    error_response = await _validate_changes_apply(
        cart, registration_service, lock=False
    )
    if error_response:
        await db.rollback()
        return error_response

    # Price the cart (this will be the official price)
    pricing_result = await cart_service.price_cart(cart, event)
    cart_entity.set_pricing_result(pricing_result)

    if not await _validate_checkout_method(
        service.value, method.value, cart, pricing_result, checkout_service
    ):
        await db.commit()
        raise NotFound

    checkout_entity, checkout = await checkout_service.create_checkout(
        service_id=service.value,
        cart_data=cart,
        pricing_result=pricing_result,
    )

    response = Response(
        200,
        content=Content(
            b"application/json",
            get_converter().dumps(
                CreateCheckoutResponse(
                    id=checkout_entity.id,
                    service=checkout.service,
                    external_id=checkout.id,
                    data=checkout.response_data,
                )
            ),
        ),
    )

    await db.commit()
    return response


@auth(RequireCart)
@app.router.put("/checkouts/{id}/cancel")
@docs(
    tags=["Checkout"],
)
@transaction
async def cancel_checkout(id: UUID, checkout_service: CheckoutService) -> Response:
    """Cancel a checkout."""
    # TODO: permissions
    result = await checkout_service.cancel_checkout(id)
    if result is None:
        raise NotFound
    elif result is True:
        return Response(204)
    else:
        raise HTTPException(409, "Checkout could not be canceled")


@auth(RequireCart)
@app.router.post("/checkouts/{id}/update")
@docs(
    responses={
        200: ResponseInfo(
            "An updated checkout", content=[ContentInfo(CreateCheckoutResponse)]
        ),
        204: ResponseInfo("Returned when the checkout was completed"),
    },
    tags=["Checkout"],
)
async def update_checkout(
    id: UUID,
    body: FromJSON[dict],
    checkout_service: CheckoutService,
    registration_service: RegistrationService,
    auth_service: AuthService,
    event_service: EventService,
    db: AsyncSession,
) -> Response:
    """Update a checkout."""
    checkout = check_not_found(await checkout_service.get_checkout(id, lock=True))

    payment_service = checkout.service
    external_id = checkout.external_id

    if not checkout.is_open:
        raise NotFound

    # TODO: permissions

    # lock rows and verify changes can be applied before completing the transaction
    if not checkout.changes_applied:
        error_response = await _validate_changes_apply(
            checkout.get_cart_data(), registration_service, lock=True
        )
        if error_response:
            await db.rollback()
            return error_response

    try:
        result = await checkout_service.update_checkout(checkout, body.value)
    except ValidationError as e:
        raise BodyValidationError(e)
    except CheckoutStateError as e:
        raise HTTPException(409, str(e))

    # After this point, any error will roll back the database but will not cancel or
    # refund the transaction

    try:
        response = await _handle_update(
            registration_service, auth_service, event_service, checkout, result
        )
        await db.commit()
        return response
    except Exception:
        # TODO: use a specific logger?
        logger.opt(exception=True).error(
            f"{payment_service!r} checkout {external_id} failed to save changes "
            f"after updating the checkout. This may need to be resolved manually."
        )
        raise


async def _handle_update(
    registration_service: RegistrationService,
    auth_service: AuthService,
    event_service: EventService,
    checkout_entity: CheckoutEntity,
    checkout_result: PaymentServiceCheckout,
):
    if (
        checkout_result.state == CheckoutState.complete
        and not checkout_entity.changes_applied
    ):
        updated = await apply_checkout_changes(
            registration_service, auth_service, checkout_entity
        )
        cart_data = checkout_entity.get_cart_data()
        event_id = cart_data.event_id

        # Assign registration numbers at the end, so the row storing the number
        # does not stay locked while updating the transaction
        event_stats = await event_service.get_event_stats(event_id, lock=True)
        assign_registration_numbers(event_stats, updated)

    if checkout_result.is_open:
        return Response(
            200,
            content=Content(
                b"application/json",
                get_converter().dumps(
                    CreateCheckoutResponse(
                        id=checkout_entity.id,
                        service=checkout_entity.service,
                        external_id=checkout_result.id,
                        data=checkout_result.response_data,
                    )
                ),
            ),
        )
    else:
        return Response(204)


async def _validate_changes_apply(
    cart_data: CartData, registration_service: RegistrationService, lock: bool
):
    invalid = await validate_changes_apply(registration_service, cart_data, lock=lock)

    if len(invalid) > 0:
        return Response(
            409,
            content=Content(
                b"application/json",
                get_converter().dumps(
                    CheckoutErrorResponse(
                        registration_ids=[r.id for r in invalid],
                    )
                ),
            ),
        )
    else:
        return None


async def _validate_checkout_method(
    service: str,
    method: str,
    cart_data: CartData,
    pricing_result: PricingResult,
    checkout_service: CheckoutService,
):
    options = await checkout_service.get_checkout_methods_for_cart(
        cart_data, pricing_result
    )
    return any(o.service == service and o.method == method for o in options)
