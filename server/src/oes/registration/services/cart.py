"""Cart service."""
from typing import Optional
from uuid import UUID

from oes.registration.entities.cart import CartEntity
from oes.registration.entities.registration import RegistrationEntity
from oes.registration.models.cart import CartData, CartRegistration
from oes.registration.models.event import Event
from oes.registration.models.pricing import PricingRequest, PricingResult
from oes.registration.pricing import default_pricing
from oes.registration.services.auth import AuthService
from oes.registration.services.registration import (
    RegistrationService,
    add_account_to_registration,
)
from sqlalchemy.ext.asyncio import AsyncSession


class CartService:
    """Cart service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_cart(self, id: str) -> Optional[CartEntity]:
        """Get a cart by its ID."""
        return await self.db.get(CartEntity, id)

    async def get_empty_cart(self, event_id: str) -> CartEntity:
        """Get the empty cart."""
        data = CartData(event_id=event_id)
        entity = CartEntity.create(data)
        saved = await self.save_cart(entity)
        return saved

    async def save_cart(self, cart: CartEntity) -> CartEntity:
        """Save a cart.

        Returns:
            The updated :class:`CartEntity`.
        """
        merged = await self.db.merge(cart)
        return merged

    async def price_cart(self, cart_data: CartData, event: Event) -> PricingResult:
        """Price a :class:`CartData`."""
        # TODO: this might make more sense to be in its own service?

        # TODO: include hooks
        req = PricingRequest(
            currency="USD",  # TODO: currency settings
            event=event,
            cart=cart_data,
        )
        result = await default_pricing(req, None)
        return result


async def validate_changes_apply(
    registration_service: RegistrationService,
    cart_data: CartData,
    *,
    lock: bool = False,
) -> list[RegistrationEntity]:
    """Validate that cart changes can be applied.

    Warning:
        Even though registration rows can be locked, two concurrent checkouts can
        create the same new registration and experience a conflict.

    Args:
        cart_data: The :class:`CartData`.
        registration_service: The :class:`RegistrationService`.
        lock: Whether to lock the registrations.

    Returns:
        A list of :class:`RegistrationEntity` which changes cannot be applied to.
    """
    invalid = []

    registrations = await registration_service.get_registrations(
        (r.id for r in cart_data.registrations), lock=lock
    )

    registrations_by_id = {r.id: r for r in registrations}
    for cart_registration in cart_data.registrations:
        entity = registrations_by_id.get(cart_registration.id)
        if entity and not entity.validate_changes_from_cart(cart_registration):
            invalid.append(entity)

    return invalid


async def apply_changes(
    registration_service: RegistrationService,
    auth_service: AuthService,
    cart_data: CartData,
) -> list[RegistrationEntity]:
    """Apply all registration changes in a checkout.

    Args:
        registration_service: The :class:`RegistrationService`.
        auth_service: The :class:`AuthService`.
        cart_data: The :class:`CartData` to apply.

    Returns:
        A list of the created/updated registrations.

    Raises:
        InvalidChangeError: If a registration is out of date.
    """
    registrations = await registration_service.get_registrations(
        (r.id for r in cart_data.registrations), lock=True
    )
    registrations_by_id = {r.id: r for r in registrations}

    results = []

    # update each registration, or create it if it doesn't exist
    for cart_registration in cart_data.registrations:
        registration_entity = registrations_by_id.get(cart_registration.id)
        if registration_entity:
            registration_entity.apply_changes_from_cart(cart_registration)
        else:
            # TODO: should we check if the old_data is blank?
            registration_entity = RegistrationEntity.create_from_cart(cart_registration)
            await registration_service.create_registration(registration_entity)
            await _add_account(cart_registration, registration_entity, auth_service)

        results.append(registration_entity)

    return results


async def _add_account(
    cart_registration: CartRegistration,
    entity: RegistrationEntity,
    service: AuthService,
):
    """Associate the registration with the account ID in the metadata."""
    meta = cart_registration.meta or {}
    account_id = meta.get("account_id")

    if account_id:
        await add_account_to_registration(UUID(account_id), entity, service)
