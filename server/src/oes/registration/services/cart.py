"""Cart service."""
import asyncio
from inspect import iscoroutinefunction
from typing import Optional
from uuid import UUID

from oes.registration.entities.cart import CartEntity
from oes.registration.entities.registration import RegistrationEntity
from oes.registration.hook.models import HookConfig, HookEvent
from oes.registration.hook.service import HookSender
from oes.registration.models.cart import CartData, CartRegistration
from oes.registration.models.config import Config
from oes.registration.models.event import Event, SimpleEventInfo
from oes.registration.models.pricing import (
    PricingEventBody,
    PricingRequest,
    PricingResult,
)
from oes.registration.pricing import default_pricing
from oes.registration.serialization import get_converter
from oes.registration.services.auth import AuthService
from oes.registration.services.registration import (
    RegistrationService,
    add_account_to_registration,
)
from sqlalchemy.ext.asyncio import AsyncSession


class CartService:
    """Cart service."""

    def __init__(self, db: AsyncSession, config: Config):
        self.db = db
        self.hook_config = config.hooks

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


async def price_cart(
    cart_data: CartData,
    currency: str,
    event: Event,
    hook_config: HookConfig,
) -> PricingResult:
    """Price a cart, calling all pricing hooks.

    Args:
        cart_data: The :class:`CartData`.
        currency: The currency.
        event: The :class:`Event`.
        hook_config: The :class:`HookConfig`.

    Returns:
        The final :class:`PricingResult`.
    """
    req = PricingRequest(
        currency=currency,
        event=SimpleEventInfo.create(event),
        cart=cart_data,
    )
    initial_result = await default_pricing(event, req)
    return await _call_pricing_hooks(req, initial_result, hook_config)


async def _call_pricing_hooks(
    request: PricingRequest,
    result: PricingResult,
    hook_config: HookConfig,
) -> PricingResult:
    """Call all pricing hooks in order."""
    cur_result = result
    for hook_entry in hook_config.get_by_event(HookEvent.cart_price):
        hook = hook_entry.get_hook()
        body = PricingEventBody(
            request=request,
            prev_result=cur_result,
        )
        body_dict = get_converter().unstructure(body)
        if iscoroutinefunction(hook):
            result_dict = await hook(body_dict)
        else:
            loop = asyncio.get_running_loop()
            result_dict = await loop.run_in_executor(None, hook, body_dict)
        cur_result = get_converter().structure(result_dict, PricingResult)

    return cur_result


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
    hook_sender: HookSender,
) -> list[RegistrationEntity]:
    """Apply all registration changes in a checkout.

    Args:
        registration_service: The :class:`RegistrationService`.
        auth_service: The :class:`AuthService`.
        cart_data: The :class:`CartData` to apply.
        hook_sender: A :class:`HookSender` instance.

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
            await registration_entity.apply_changes_from_cart(
                cart_registration, hook_sender
            )
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
