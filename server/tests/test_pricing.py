import uuid

import pytest
from oes.registration.models.cart import CartData, CartRegistration
from oes.registration.models.event import EventConfig
from oes.registration.models.pricing import PricingRequest
from oes.registration.pricing import default_pricing, get_added_option_ids


def test_get_added_option_ids():
    old_data = {"option_ids": ["a", "b"]}

    new_data = {"option_ids": ["b", "c"]}

    assert get_added_option_ids(old_data, new_data) == {"c"}


@pytest.mark.asyncio
async def test_eval_line_items(example_events: EventConfig):
    id_ = uuid.uuid4()
    request = PricingRequest(
        currency="USD",
        event=example_events.get_event("example-event"),
        cart=CartData(
            event_id="example-event",
            registrations=(
                CartRegistration(
                    id=id_,
                    old_data={"id": str(id_), "option_ids": []},
                    new_data={"id": str(id_), "option_ids": ["attendee"]},
                ),
            ),
        ),
    )

    result = await default_pricing(request, None)
    assert result.total_price == 4500
    assert len(result.line_items) == 1
    assert result.line_items[0].price == 5000
    assert result.line_items[0].total_price == 4500
