"""Mock payment service."""
import uuid
from typing import Any, Iterable, Optional

from oes.registration.entities.checkout import CheckoutState
from oes.registration.models.payment import PaymentServiceCheckout
from oes.registration.payment.base import (
    CheckoutCancelError,
    CheckoutMethod,
    CheckoutMethodsRequest,
    CheckoutStateError,
    CreateCheckoutRequest,
    PaymentService,
    UpdateRequest,
    ValidationError,
)
from oes.registration.util import get_now


class MockPaymentService(PaymentService):
    """Mock payment service."""

    id = "mock"
    name = "Mock"

    def _get_checkout(
        self, id: str, extra_data: Optional[dict[str, Any]]
    ) -> PaymentServiceCheckout:
        extra_data = extra_data or {}
        state = CheckoutState(extra_data.get("state", CheckoutState.pending))
        return PaymentServiceCheckout(
            service=self.id, id=id, state=state, checkout_data={"state": state.value}
        )

    async def get_checkout(
        self, id: str, extra_data: Optional[dict[str, Any]] = None
    ) -> Optional[PaymentServiceCheckout]:
        return self._get_checkout(id, extra_data)

    async def get_checkout_methods(
        self, request: CheckoutMethodsRequest
    ) -> Iterable[CheckoutMethod]:
        return [CheckoutMethod(service=self.id, method="mock-card", name="Mock Card")]

    async def create_checkout(
        self, request: CreateCheckoutRequest
    ) -> PaymentServiceCheckout:
        id_ = str(uuid.uuid4())
        return PaymentServiceCheckout(
            service=self.id,
            id=id_,
            state=CheckoutState.pending,
            date_created=get_now(),
            checkout_data={
                "state": CheckoutState.pending.value,
            },
        )

    async def cancel_checkout(
        self, id: str, extra_data: Optional[dict[str, Any]] = None
    ) -> PaymentServiceCheckout:
        checkout = self._get_checkout(id, extra_data)
        if checkout.state == CheckoutState.complete:
            raise CheckoutCancelError("Checkout is already complete")
        elif checkout.state == CheckoutState.canceled:
            return PaymentServiceCheckout(
                service=self.id,
                id=self.id,
                state=checkout.state,
                checkout_data=checkout.checkout_data,
            )
        else:
            return PaymentServiceCheckout(
                service=self.id,
                id=id,
                state=CheckoutState.canceled,
                date_closed=get_now(),
                checkout_data={
                    "state": CheckoutState.canceled.value,
                },
            )

    async def _update_handler(self, request: UpdateRequest) -> PaymentServiceCheckout:
        checkout = self._get_checkout(request.id, request.checkout_data)
        if checkout.state == CheckoutState.complete:
            raise CheckoutStateError("Checkout is already complete")
        elif checkout.state == CheckoutState.canceled:
            raise CheckoutCancelError("Checkout is canceled")

        card = request.body.get("card")
        try:
            int(card)
        except (TypeError, ValueError):
            raise ValidationError("Invalid card")

        return PaymentServiceCheckout(
            service=self.id,
            id=checkout.id,
            state=CheckoutState.complete,
            date_closed=get_now(),
            checkout_data={
                "state": CheckoutState.complete.value,
            },
        )

    update_handler = _update_handler


def create_mock_service(
    config: dict[str, Any],
) -> Optional[MockPaymentService]:
    """Factory to create the :class:`MockPaymentService`."""
    return MockPaymentService()
