"""Cart views."""
import uuid
from typing import Any, Optional, Union
from uuid import UUID

from attrs import frozen
from blacksheep import (
    Content,
    FromJSON,
    FromQuery,
    HTTPException,
    Request,
    Response,
    auth,
)
from blacksheep.exceptions import NotFound
from blacksheep.messages import get_absolute_url_to_path
from blacksheep.server.openapi.common import ContentInfo, RequestBodyInfo, ResponseInfo
from blacksheep.url import build_absolute_url
from cattrs import BaseValidationError
from oes.interview.response import IncompleteInterviewStateResponse
from oes.interview.state import InvalidStateError
from oes.registration.app import app
from oes.registration.auth.handlers import RequireAdmin, RequireCart, RequireSelfService
from oes.registration.auth.oauth.user import User
from oes.registration.database import transaction
from oes.registration.docs import docs, docs_helper, serialize
from oes.registration.entities.cart import CartEntity
from oes.registration.entities.registration import RegistrationEntity
from oes.registration.models.cart import CartData, CartError, CartRegistration
from oes.registration.models.config import Config
from oes.registration.models.event import Event, EventConfig
from oes.registration.models.pricing import PricingResult
from oes.registration.models.registration import Registration, RegistrationState
from oes.registration.serialization import get_config_converter, get_converter
from oes.registration.services.cart import CartService, price_cart
from oes.registration.services.interview import InterviewService
from oes.registration.services.registration import (
    RegistrationService,
    get_allowed_add_interviews,
    get_allowed_change_interviews,
)
from oes.registration.util import check_not_found, get_now
from oes.registration.views.parameters import AttrsBody
from oes.registration.views.responses import BodyValidationError, PricingResultResponse


@frozen
class AddRegistrationDirectRequest:
    """Request body to add a registration directly to a cart."""

    registration: dict[str, Any]
    meta: Optional[dict[str, Any]] = None


@frozen
class AddRegistrationFromInterviewRequest:
    """Add a registration from a completed interview."""

    state: str


AddRegistrationRequest = Union[
    AddRegistrationDirectRequest, AddRegistrationFromInterviewRequest
]


@auth(RequireAdmin)
@app.router.post("/carts")
@docs(tags=["Cart"], responses={303: ResponseInfo("Redirect to the created cart")})
@transaction
async def create_cart(
    request: Request,
    body: AttrsBody[CartData],
    service: CartService,
    event_config: EventConfig,
) -> Response:
    """Create a cart."""
    cart_data = body.value

    # Check that the event exists
    event = event_config.get_event(cart_data.event_id)
    if not event:
        raise BodyValidationError(
            ValueError(f"Event ID not found: {cart_data.event_id}")
        )

    # Check that the new data is valid for each registration
    for cr in cart_data.registrations:
        _validate_registration(cr.new_data)

    # Create the cart
    entity = CartEntity.create(cart_data)
    entity = await service.save_cart(entity)

    # Redirect to new cart URL
    url = get_absolute_url_to_path(request, f"/carts/{entity.id}")

    return Response(
        303,
        headers=[
            (b"Location", url.value),
        ],
    )


@auth(RequireCart)
@app.router.get("/carts/empty")
@docs(
    responses={
        303: ResponseInfo("Redirect to the cart"),
    },
    tags=["Cart"],
)
@transaction
async def read_empty_cart(
    event_id: FromQuery[str],
    request: Request,
    service: CartService,
    event_config: EventConfig,
    user: User,
) -> Response:
    """Get an empty cart."""
    event = check_not_found(event_config.get_event(event_id.value))
    if not event.is_visible_to(user):
        raise NotFound

    cart_entity = await service.get_empty_cart(event.id)
    cart_url = get_absolute_url_to_path(request, f"/carts/{cart_entity.id}")
    return Response(
        303,
        headers=[
            (b"Location", cart_url.value),
        ],
    )


@auth(RequireCart)
@app.router.get("/carts/{id}")
@docs(
    responses={200: ResponseInfo("The cart data", content=[ContentInfo(CartData)])},
    tags=["Cart"],
)
async def read_cart(id: str, service: CartService) -> Response:
    """Read a cart."""
    cart = check_not_found(await service.get_cart(id))

    model = cart.get_cart_data_model()
    data_bytes = get_converter().dumps(model)

    return Response(
        200,
        headers=[
            (b"ETag", f'"{cart.id}"'.encode()),
        ],
        content=Content(
            b"application/json",
            data_bytes,
        ),
    )


@auth(RequireCart)
@app.router.get("/carts/{id}/pricing-result")
@docs_helper(
    response_type=PricingResultResponse,
    response_summary="The pricing result",
    tags=["Cart"],
)
@transaction
async def read_cart_pricing_result(
    id: str,
    service: CartService,
    event_config: EventConfig,
    config: Config,
) -> PricingResultResponse:
    """Get the cart pricing result."""
    cart = check_not_found(await service.get_cart(id))
    model = cart.get_cart_data_model()

    # don't price an empty cart
    if len(model.registrations) == 0:
        return PricingResultResponse(
            line_items=[],
            total_price=0,
        )

    if cart.pricing_result is None:
        event = check_not_found(event_config.get_event(model.event_id))

        result = await price_cart(
            model,
            config.payment.currency,
            event,
            config.hooks,
        )

        # since the pricing result here is not final, no need to lock anything
        cart.set_pricing_result(result)
    else:
        result = get_converter().structure(cart.pricing_result, PricingResult)

    return PricingResultResponse.create(result)


@auth(RequireCart)
@app.router.post("/carts/{id}/registrations")
@docs(
    request_body=RequestBodyInfo(
        description="The registration info, or interview state",
        examples={
            "direct": {
                "registration": {
                    "id": "105e8d85-4f06-42b4-98c0-11c3cd0fe3c6",
                    "event_id": "example-event",
                    "state": "created",
                    "date_created": "2020-01-01T12:00:00+00:00",
                    "version": 1,
                    "option_ids": ["attendee"],
                },
                "meta": {
                    "is_minor": True,
                },
            },
            "interview": {
                "state": "ZXhhbXBsZQ==",
            },
        },
    ),
    responses={303: ResponseInfo("Redirect to the new cart")},
    tags=["Cart"],
)
@transaction
async def add_registration_to_cart(
    id: str,
    request: Request,
    service: CartService,
    reg_service: RegistrationService,
    interview_service: InterviewService,
    event_config: EventConfig,
    body: FromJSON[dict[str, Any]],
    user: User,
) -> Response:
    """Add a registration to a cart."""
    add_obj = _parse_add_body(body.value)

    cart_entity = check_not_found(await service.get_cart(id))
    cart = cart_entity.get_cart_data_model()
    event = check_not_found(event_config.get_event(cart.event_id))
    if not event.is_open_to(user):
        raise HTTPException(409)

    if isinstance(add_obj, AddRegistrationDirectRequest):
        new_cart_entity = await _add_direct(cart, add_obj, service, reg_service)
    else:
        current_url = build_absolute_url(
            request.scheme.encode(),
            request.host.encode(),
            request.base_path.encode(),
            request.url.path,
        ).value.decode()

        new_cart_entity = await _add_from_interview(
            cart,
            event,
            add_obj.state,
            current_url,
            service,
            reg_service,
            interview_service,
        )

    cart_url = get_absolute_url_to_path(request, f"/carts/{new_cart_entity.id}")

    return Response(
        303,
        headers=[
            (b"Location", cart_url.value),
        ],
    )


@auth(RequireCart)
@app.router.delete("/carts/{id}/registrations/{registration_id}")
@docs(
    responses={
        303: ResponseInfo("Redirect to the new cart"),
    },
    tags=["Cart"],
)
@transaction
async def remove_registration_from_cart(
    id: str,
    registration_id: UUID,
    request: Request,
    service: CartService,
    events: EventConfig,
    user: User,
) -> Response:
    """Remove a registration from a cart."""
    entity = check_not_found(await service.get_cart(id))
    cart = entity.get_cart_data_model()

    event = events.get_event(cart.event_id)
    if not event or not event.is_open_to(user):
        raise HTTPException(409)

    updated = cart.remove_registration(registration_id)
    if updated == cart:
        raise NotFound

    new_entity = CartEntity.create(updated)
    new_entity = await service.save_cart(new_entity)

    cart_url = get_absolute_url_to_path(request, f"/carts/{new_entity.id}")

    return Response(
        303,
        headers=[
            (b"Location", cart_url.value),
        ],
    )


@auth(RequireSelfService)
@app.router.get("/carts/{id}/new-interview")
@docs(
    responses={
        200: ResponseInfo(
            "An interview state response",
        )
    },
    tags=["Cart"],
)
@serialize(IncompleteInterviewStateResponse)
async def create_cart_add_interview_state(
    request: Request,
    id: str,
    interview_id: FromQuery[str],
    registration_id: FromQuery[Optional[UUID]],
    config: Config,
    event_config: EventConfig,
    service: CartService,
    registration_service: RegistrationService,
    interview_service: InterviewService,
    user: User,
) -> IncompleteInterviewStateResponse:
    """Get an interview state to add a registration to a cart."""
    entity = check_not_found(await service.get_cart(id))
    cart = entity.get_cart_data_model()

    event = check_not_found(event_config.get_event(cart.event_id))
    if not event.is_open_to(user):
        raise HTTPException(409)

    if registration_id.value is not None:
        registration = await _get_registration_for_change(
            registration_id.value, registration_service, user
        )
    else:
        registration = None

    valid_interview_id = _check_interview_availability(
        interview_id.value, event, registration
    )

    # Build state
    context = _get_interview_context(event)
    initial_data = _get_interview_initial_data(event.id, registration, user)
    submission_id = uuid.uuid4()

    target_url = get_absolute_url_to_path(request, f"/carts/{entity.id}/registrations")

    state = interview_service.create_state(
        valid_interview_id,
        target_url=target_url.value.decode(),
        submission_id=submission_id,
        context=context,
        initial_data=initial_data,
    )

    return IncompleteInterviewStateResponse(
        state=state,
        update_url=config.interview.update_url,
        content=None,
    )


def _validate_registration(data: dict[str, Any]) -> Registration:
    """Validate that a :class:`Registration` is valid."""
    try:
        return get_converter().structure(data, Registration)
    except BaseValidationError as e:
        raise BodyValidationError(e)


async def _get_registration_for_change(
    id: UUID,
    service: RegistrationService,
    user: User,
) -> RegistrationEntity:
    reg = await service.get_registration(id, include_accounts=True)
    if not reg:
        raise NotFound

    # Check that the user account is assocated with this registration
    # TODO: check emails also
    if user.id not in [a.id for a in reg.accounts]:
        raise NotFound

    return reg


def _get_interview_context(event: Event) -> dict[str, Any]:
    event_data = get_config_converter().unstructure(event)
    return {
        "event": event_data,
    }


def _get_interview_initial_data(
    event_id: str,
    registration: Optional[RegistrationEntity],
    user: Optional[User],
) -> dict[str, Any]:
    if registration:
        model = registration.get_model()
        registration_data = get_converter().unstructure(model)
        meta = {}
    else:
        model = Registration(
            id=uuid.uuid4(),
            state=RegistrationState.created,
            event_id=event_id,
            version=1,
            date_created=get_now(),
        )
        registration_data = get_converter().unstructure(model)

        meta = (
            {
                "account_id": str(user.id),
            }
            if user
            else {}
        )

    return {
        "registration": registration_data,
        "meta": meta,
    }


async def _add_direct(
    cart: CartData,
    add: AddRegistrationDirectRequest,
    service: CartService,
    reg_service: RegistrationService,
):
    new_reg = _parse_registration_data(add.registration)

    # Get existing data
    cur_reg_entity = await reg_service.get_registration(new_reg.id)

    return await _add_to_cart(cart, cur_reg_entity, new_reg, None, add.meta, service)


async def _add_from_interview(
    cart: CartData,
    event: Event,
    state: str,
    current_url: str,
    service: CartService,
    reg_service: RegistrationService,
    interview_service: InterviewService,
):
    try:
        interview_result = interview_service.get_validated_state(
            state, current_url=current_url
        )
    except InvalidStateError as e:
        raise HTTPException(409, str(e))

    # Get existing data
    new_reg = _parse_registration_data(interview_result.data.get("registration", {}))
    cur_reg_entity = await reg_service.get_registration(new_reg.id)

    # make sure interview is still available
    _check_interview_availability(
        interview_result.interview_id,
        event,
        cur_reg_entity,
    )

    # Add to cart
    meta = interview_result.data.get("meta")
    return await _add_to_cart(
        cart, cur_reg_entity, new_reg, interview_result.submission_id, meta, service
    )


def _parse_add_body(body: dict[str, Any]) -> AddRegistrationRequest:
    try:
        obj = get_converter().structure(body, AddRegistrationRequest)
    except BaseValidationError as e:
        raise BodyValidationError(e) from e
    return obj


def _check_interview_availability(
    interview_id: str,
    event: Event,
    registration: Optional[RegistrationEntity],
) -> str:
    """Raise not found if the interview is not permitted."""
    if registration:
        allowed = get_allowed_change_interviews(event, registration)
    else:
        allowed = get_allowed_add_interviews(event)

    if interview_id not in [o.id for o in allowed]:
        raise NotFound
    return interview_id


def _parse_registration_data(data: dict[str, Any]) -> Registration:
    try:
        registration = get_converter().structure(data, Registration)
    except BaseValidationError as e:
        raise BodyValidationError(e)
    return registration


async def _add_to_cart(
    cart: CartData,
    old_reg: Optional[RegistrationEntity],
    new_reg: Registration,
    submission_id: Optional[str],
    meta: Optional[dict[str, Any]],
    service: CartService,
) -> CartEntity:
    cr = CartRegistration.create(
        old_reg, new_reg, submission_id=submission_id, meta=meta
    )

    try:
        new_cart = cart.add_registration(cr)
    except CartError as e:
        raise HTTPException(409, str(e))

    entity = CartEntity.create(new_cart)
    return await service.save_cart(entity)
