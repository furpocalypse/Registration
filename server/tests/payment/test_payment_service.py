import pytest
from oes.registration.entities.checkout import CheckoutState
from oes.registration.payment.base import CreateCheckoutRequest, PaymentService


@pytest.mark.asyncio
async def test_checkout(
    payment_service: PaymentService, checkout_request: CreateCheckoutRequest
):
    created = await payment_service.create_checkout(checkout_request)
    assert created.state == CheckoutState.pending

    fetched = await payment_service.get_checkout(
        created.id, extra_data=created.checkout_data
    )
    assert fetched.id == created.id
    assert fetched.state == CheckoutState.pending

    canceled = await payment_service.cancel_checkout(
        fetched.id, extra_data=fetched.checkout_data
    )

    assert canceled.id == fetched.id
    assert canceled.state == CheckoutState.canceled

    # second cancel to make sure it is handled gracefully
    canceled = await payment_service.cancel_checkout(
        fetched.id, extra_data=fetched.checkout_data
    )
    assert canceled.id == fetched.id
