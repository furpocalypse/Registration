import os
import uuid

import pytest
import pytest_asyncio
from oes.registration.models.cart import CartData, CartRegistration
from oes.registration.models.pricing import LineItem, PricingResult
from oes.registration.payment.base import CreateCheckoutRequest, PaymentService
from oes.registration.payment.stripe import StripeConfig, StripePaymentService


def make_stripe_service():
    secret_key = os.getenv("TEST_STRIPE_SECRET_KEY")
    if not secret_key:
        pytest.skip("TEST_STRIPE_SECRET_KEY not set")

    try:
        import stripe  # noqa
    except ImportError:
        pytest.skip("stripe library not installed")

    return StripePaymentService(
        StripeConfig(
            "",
            secret_key,
        )
    )


@pytest.fixture(
    params=[
        make_stripe_service,
    ]
)
def payment_service(request):
    service = request.param()
    return service


@pytest.fixture
def checkout_request(payment_service: PaymentService):
    id_ = uuid.uuid4()
    req = CreateCheckoutRequest(
        service=payment_service.id,
        cart_data=CartData(
            event_id="example-event",
            registrations=(
                CartRegistration(
                    id=uuid.uuid4(),
                    old_data={},
                    new_data={},
                ),
            ),
        ),
        pricing_result=PricingResult(
            currency="USD",
            line_items=(
                LineItem(
                    registration_id=id_,
                    type_id="item1",
                    name="Test Item",
                    price=1000,
                    total_price=1000,
                ),
            ),
            total_price=1000,
        ),
    )

    return req


@pytest_asyncio.fixture
async def created_checkout_request(
    checkout_request: CreateCheckoutRequest, payment_service: PaymentService
):
    return await payment_service.create_checkout(checkout_request)
