"""Checkout service module."""
import asyncio
import copy
import itertools
from typing import Any, Optional, Union, overload
from uuid import UUID

from oes.registration.auth.account_service import AccountService
from oes.registration.entities.checkout import CheckoutEntity, CheckoutState
from oes.registration.entities.registration import RegistrationEntity
from oes.registration.hook.models import HookEvent
from oes.registration.hook.service import HookSender
from oes.registration.log import AuditLogType, audit_log
from oes.registration.models.cart import CartData
from oes.registration.models.payment import PaymentServiceCheckout
from oes.registration.models.pricing import PricingResult
from oes.registration.payment.base import (
    CheckoutCancelError,
    CheckoutMethod,
    CheckoutMethodsRequest,
    CheckoutStateError,
    CreateCheckoutRequest,
    PaymentService,
    UpdateRequest,
)
from oes.registration.payment.config import PaymentServices
from oes.registration.services.cart import apply_changes
from oes.registration.services.registration import RegistrationService
from oes.registration.util import get_now
from sqlalchemy.ext.asyncio import AsyncSession


class CheckoutService:
    """Checkout service."""

    def __init__(
        self,
        db: AsyncSession,
        payment_services: PaymentServices,
        hook_sender: HookSender,
    ):
        self.db = db
        self.payment_services = payment_services
        self.hook_sender = hook_sender

    def is_service_available(self, id: str) -> bool:
        """Get whether the given service is configured and loaded."""
        return id in list(self.payment_services.get_available_services())

    def get_payment_service(self, id: str) -> PaymentService:
        """Get a payment service by ID."""
        res = self.payment_services.get_service(id)
        if not res:
            raise LookupError(f"Payment service not found {id}")
        return res

    async def get_checkout_methods_for_cart(
        self, cart_data: CartData, pricing_result: PricingResult
    ) -> list[CheckoutMethod]:
        """Get a collection of available checkout methods for a cart."""
        tasks = []
        for service_id in self.payment_services.get_available_services():
            service = self.payment_services.get_service(service_id)
            if not service:
                continue

            tasks.append(
                service.get_checkout_methods(
                    CheckoutMethodsRequest(
                        service=service.id,
                        cart_data=cart_data,
                        pricing_result=pricing_result,
                    )
                )
            )

        return list(itertools.chain.from_iterable(await asyncio.gather(*tasks)))

    async def get_checkout(
        self, id: UUID, *, lock: bool = False
    ) -> Optional[CheckoutEntity]:
        """Get a checkout by ID."""
        obj = await self.db.get(CheckoutEntity, id, with_for_update=lock)
        return obj

    async def create_checkout(
        self,
        service_id: str,
        cart_data: CartData,
        pricing_result: PricingResult,
        method: Optional[str] = None,
    ) -> tuple[CheckoutEntity, PaymentServiceCheckout]:
        """Create a checkout in an external service.

         Creates a :class:`CheckoutEntity` to represent the created checkout.

        Args:
            service_id: The payment service ID.
            cart_data: The cart data.
            pricing_result: The pricing result.
            method: Payment method type.

        Returns:
            A pair of the new :class:`CheckoutEntity` and the
                :class:`PaymentServiceCheckout`.
        """
        service = self.get_payment_service(service_id)
        entity = CheckoutEntity(
            state=CheckoutState.pending,
            service=service.id,
        )
        entity.set_cart_data(cart_data)
        entity.set_pricing_result(pricing_result)

        request = CreateCheckoutRequest(
            service=service_id,
            method=method,
            cart_data=cart_data,
            pricing_result=pricing_result,
        )

        checkout = await service.create_checkout(request)

        entity.set_service_info(
            service.id,
            external_id=checkout.id,
            external_data=checkout.checkout_data,
        )

        self.db.add(entity)
        await self.db.flush()

        await self.hook_sender.schedule_hooks_for_event(
            HookEvent.checkout_created,
            checkout,
        )

        audit_log.bind(type=AuditLogType.checkout_create).success(
            "Checkout {checkout} created, method {}",
            method,
            checkout=entity,
        )

        return entity, checkout

    @overload
    async def get_checkout_status(
        self,
        *,
        service_id: str,
        external_id: str,
        extra_data: Optional[dict[str, Any]] = None,
    ) -> Optional[PaymentServiceCheckout]:
        ...

    @overload
    async def get_checkout_status(
        self, checkout: Union[CheckoutEntity, PaymentServiceCheckout]
    ) -> Optional[PaymentServiceCheckout]:
        ...

    async def get_checkout_status(
        self,
        checkout: Union[CheckoutEntity, PaymentServiceCheckout, None] = None,
        service_id: Union[str, CheckoutEntity, PaymentServiceCheckout, None] = None,
        external_id: Optional[str] = None,
        extra_data: Optional[dict[str, Any]] = None,
    ) -> Optional[PaymentServiceCheckout]:
        """Get a :class:`PaymentServiceCheckout` from an external service.

        Args:
            checkout: A checkout class or entity.
            service_id: The payment service ID.
            external_id: The ID in the payment service.
            extra_data: Additional data about the checkout.

        Returns:
            The :class:`PaymentServiceCheckout`, or None if not found.
        """
        if isinstance(checkout, CheckoutEntity):
            service_id = checkout.service
            external_id = checkout.external_id
            extra_data = checkout.external_data
        elif isinstance(checkout, PaymentServiceCheckout):
            service_id = checkout.service
            external_id = checkout.id
            extra_data = checkout.checkout_data

        if service_id is None or external_id is None:
            raise ValueError("Invalid arguments")

        service = self.get_payment_service(service_id)
        res = await service.get_checkout(external_id, extra_data)
        return res

    async def validate_changes(
        self,
        checkout_entity: CheckoutEntity,
        registration_service: RegistrationService,
        *,
        lock: bool = False,
    ) -> list[RegistrationEntity]:
        """Validate that cart changes can be applied.

        Warning:
            Even though registration rows can be locked, two concurrent checkouts can
            create the same new registration and experience a conflict.

        Args:
            checkout_entity: The :class:`CheckoutEntity`.
            registration_service: The :class:`RegistrationService`.
            lock: Whether to lock the registrations.

        Returns:
            A list of :class:`RegistrationEntity` which changes cannot be applied to.
        """
        invalid = []

        cart_data = checkout_entity.get_cart_data()
        registrations = await registration_service.get_registrations(
            (r.id for r in cart_data.registrations), lock=lock
        )
        registrations_by_id = {r.id: r for r in registrations}
        for cart_registration in cart_data.registrations:
            entity = registrations_by_id.get(cart_registration.id)
            if entity and not entity.validate_changes_from_cart(cart_registration):
                invalid.append(entity)

        return invalid

    async def cancel_checkout(
        self,
        id: UUID,
    ) -> Optional[bool]:
        """Cancel a checkout by ID.

        Returns:
            True if cancellation succeeded, False if it could not be canceled, or None
                if it is non-existent or already canceled.
        """
        checkout = await self.get_checkout(id, lock=True)
        if not checkout or checkout.state == CheckoutState.canceled:
            return None

        if checkout.state == CheckoutState.complete:
            return False

        if not self.is_service_available(checkout.service):
            return False

        service = self.get_payment_service(checkout.service)

        try:
            result = await service.cancel_checkout(
                checkout.external_id, checkout.external_data
            )
        except CheckoutCancelError:
            return False

        if result.state != CheckoutState.canceled:
            return False

        if checkout.cancel(result.date_closed):
            await self.hook_sender.schedule_hooks_for_event(
                HookEvent.checkout_canceled,
                PaymentServiceCheckout(
                    service=checkout.service,
                    id=checkout.external_id,
                    state=checkout.state,
                    date_created=checkout.date_created,
                    date_closed=checkout.date_closed,
                    checkout_data=checkout.external_data,
                ),
            )
        return True

    def _apply_updated_checkout(
        self, current: CheckoutEntity, result: PaymentServiceCheckout
    ):
        """Update the checkout entity with the data returned in the checkout result.

        Mutates ``current``.
        """
        # TODO: differences between doing this and using the .cancel/complete methods
        cur_state = current.state
        new_state = result.state

        # set date_closed
        if cur_state == CheckoutState.pending and new_state != CheckoutState.pending:
            current.date_closed = (
                result.date_closed if result.date_closed is not None else get_now()
            )
        elif result.date_closed is not None:
            current.date_closed = result.date_closed

        if result.date_created is not None:
            current.date_created = result.date_created

        if result.checkout_data:
            current.external_data = copy.deepcopy(result.checkout_data)

        current.state = new_state
        current.external_id = result.id

    async def update_checkout(
        self, checkout: CheckoutEntity, body: dict[str, Any]
    ) -> PaymentServiceCheckout:
        """Update a checkout via the payment service.

        Mutates the ``checkout``.

        Args:
            checkout: The :class:`CheckoutEntity`.
            body: Data sent from the client.

        Returns:
            The updated :class:`PaymentServiceCheckout``.

        Raises:
            CheckoutStateError: If the payment service does not support this,
                or if the checkout is not updatable.
        """
        if checkout.state != CheckoutState.pending:
            raise CheckoutStateError("Checkout is already closed")

        service = self.get_payment_service(checkout.service)
        if not service.update_handler:
            raise CheckoutStateError("Not supported")

        req = UpdateRequest(
            service=service.id,
            id=checkout.external_id,
            checkout_data=copy.deepcopy(checkout.external_data),
            body=body,
        )

        result = await service.update_handler(req)
        self._apply_updated_checkout(checkout, result)

        if result.state == CheckoutState.complete:
            audit_log.bind(type=AuditLogType.checkout_complete).success(
                "Checkout {checkout} completed", checkout=checkout
            )
            await self.hook_sender.schedule_hooks_for_event(
                HookEvent.checkout_closed, result
            )

        return result


async def apply_checkout_changes(
    registration_service: RegistrationService,
    account_service: AccountService,
    checkout_entity: CheckoutEntity,
    hook_sender: HookSender,
) -> list[RegistrationEntity]:
    """Apply all registration changes in a checkout.

    Marks the ``checkout_entity`` as having been applied.

    Args:
        registration_service: The :class:`RegistrationService`.
        account_service: The :class:`AccountService`.
        checkout_entity: The :class:`CheckoutEntity` to apply.
        hook_sender: The hook sender.

    Returns:
        A list of the created/updated registrations.

    Raises:
        InvalidChangeError: If a registration is out of date.
    """
    if checkout_entity.state != CheckoutState.complete:
        raise CheckoutStateError("Checkout is not complete")

    if checkout_entity.changes_applied:
        raise CheckoutStateError("Changes have already been applied")

    cart_data = checkout_entity.get_cart_data()

    results = await apply_changes(
        registration_service, account_service, cart_data, hook_sender
    )

    checkout_entity.changes_applied = True
    return results
