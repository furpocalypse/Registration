"""Stripe module."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from attrs import field, frozen
from loguru import logger
from oes.registration.entities.checkout import CheckoutState
from oes.registration.models.payment import PaymentServiceCheckout
from oes.registration.payment.base import (
    CheckoutCancelError,
    CheckoutMethod,
    CheckoutMethodsRequest,
    CreateCheckoutRequest,
    PaymentService,
    PaymentServiceError,
    UpdateRequest,
    ValidationError,
)
from oes.registration.serialization import get_config_converter

try:
    import stripe
    import stripe.error
except ImportError:
    stripe = None


@frozen
class StripeConfig:
    """Stripe configuration."""

    publishable_key: str
    secret_key: str = field(repr=False)


class StripePaymentService(PaymentService):
    """Stripe integration."""

    id = "stripe"
    name = "Stripe"
    config: StripeConfig

    def __init__(self, config: StripeConfig):
        self.config = config

    def _get_intent(self, id: str) -> Optional[stripe.PaymentIntent]:
        try:
            intent = stripe.PaymentIntent.retrieve(
                id,
                api_key=self.config.secret_key,
            )
        except stripe.error.InvalidRequestError:
            return None
        return intent

    async def get_checkout(
        self, id: str, extra_data: Optional[dict[str, Any]] = None
    ) -> Optional[PaymentServiceCheckout]:
        loop = asyncio.get_running_loop()
        intent = await loop.run_in_executor(None, self._get_intent, id)
        if intent is None:
            return None

        checkout = PaymentServiceCheckout(
            service=self.id,
            id=intent.stripe_id,
            state=_get_checkout_state(intent),
            date_created=datetime.fromtimestamp(intent.created, tz=timezone.utc),
            date_closed=datetime.fromtimestamp(intent.canceled_at, tz=timezone.utc)
            if intent.get("canceled_at") is not None
            else None,
            response_data={
                "publishable_key": self.config.publishable_key,
            },
        )
        return checkout

    async def get_checkout_methods(
        self, request: CheckoutMethodsRequest
    ) -> Iterable[CheckoutMethod]:
        # TODO
        return [CheckoutMethod(service=self.id, method="card", name="Card")]

    def _create_intent(self, request: CreateCheckoutRequest) -> stripe.PaymentIntent:
        # Create a PaymentIntent
        intent = stripe.PaymentIntent.create(
            api_key=self.config.secret_key,
            idempotency_key=str(uuid.uuid4()),
            currency=request.pricing_result.currency.lower(),
            amount=request.pricing_result.total_price,
            confirmation_method="manual",
            # TODO: customers?
            # TODO: email?
        )
        return intent

    async def create_checkout(
        self, request: CreateCheckoutRequest
    ) -> PaymentServiceCheckout:
        loop = asyncio.get_running_loop()
        intent = await loop.run_in_executor(None, self._create_intent, request)

        checkout_info = PaymentServiceCheckout(
            service=self.id,
            id=intent.stripe_id,
            state=CheckoutState.pending,
            date_created=datetime.fromtimestamp(intent.created, tz=timezone.utc),
            response_data={
                "publishable_key": self.config.publishable_key,
                "amount": request.pricing_result.total_price,
                "currency": request.pricing_result.currency.lower(),
            },
        )
        return checkout_info

    def _cancel_intent(self, id: str):
        intent = self._get_intent(id)
        if not intent:
            return False

        if intent.status == "canceled":
            return intent

        try:
            return stripe.PaymentIntent.cancel(
                intent,
                api_key=self.config.secret_key,
            )
        except stripe.error.InvalidRequestError:
            return False

    async def cancel_checkout(
        self, id: str, extra_data: Optional[dict[str, Any]] = None
    ) -> PaymentServiceCheckout:
        loop = asyncio.get_running_loop()
        intent = await loop.run_in_executor(None, self._cancel_intent, id)
        if intent is False:
            raise CheckoutCancelError

        checkout = PaymentServiceCheckout(
            service=self.id,
            id=intent.stripe_id,
            state=_get_checkout_state(intent),
            date_created=datetime.fromtimestamp(intent.created, tz=timezone.utc),
            date_closed=datetime.fromtimestamp(intent.canceled_at, tz=timezone.utc)
            if "canceled_at" in intent
            else None,
        )
        return checkout

    def _confirm_intent(self, id: str, payment_method: str) -> stripe.PaymentIntent:
        try:
            intent = stripe.PaymentIntent.confirm(
                id,
                api_key=self.config.secret_key,
                payment_method=payment_method,
            )
        except stripe.error.CardError:
            # TODO: parse error messages?
            raise PaymentServiceError
        except stripe.error.InvalidRequestError:
            raise PaymentServiceError
        return intent

    async def _update_handler(self, request: UpdateRequest) -> PaymentServiceCheckout:
        payment_method = request.body.get("payment_method")
        if payment_method is None or not isinstance(payment_method, str):
            raise ValidationError

        loop = asyncio.get_running_loop()
        intent = await loop.run_in_executor(
            None, self._confirm_intent, request.id, payment_method
        )

        state = _get_checkout_state(intent)

        if intent.status == "requires_action":
            response_data = {
                "client_secret": intent.client_secret,
                "next_action": True,
            }
        else:
            response_data = {}

        return PaymentServiceCheckout(
            service=self.id,
            id=intent.stripe_id,
            state=state,
            date_created=datetime.fromtimestamp(intent.created, tz=timezone.utc),
            response_data=response_data,
        )

    update_handler = _update_handler


def _get_checkout_state(intent: stripe.PaymentIntent) -> CheckoutState:
    if intent.status == "succeeded":
        return CheckoutState.complete
    elif intent.status == "canceled":
        return CheckoutState.canceled
    else:
        return CheckoutState.pending


def create_stripe_service(
    config: dict[str, Any],
) -> Optional[StripePaymentService]:
    """Factory to create the :class:`StripePaymentService`."""
    # ensure stripe is available
    if stripe is None:
        logger.info("Stripe library is not installed")
        return None

    try:
        config_obj = get_config_converter().structure(config, StripeConfig)
    except Exception as e:
        logger.opt(exception=e).warning("Failed to load Stripe configuration")
        return None

    service = StripePaymentService(config_obj)
    return service
