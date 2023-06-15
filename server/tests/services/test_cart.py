import uuid
from unittest.mock import create_autospec

import pytest
import pytest_asyncio
from oes.registration.entities.cart import CartEntity
from oes.registration.models.cart import CartData, CartRegistration
from oes.registration.models.config import Config
from oes.registration.services.cart import CartService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def service(db: AsyncSession):
    return CartService(db, create_autospec(Config))


@pytest_asyncio.fixture
async def cart_id(service: CartService, db: AsyncSession):
    id = uuid.uuid4()
    cart_data = CartData(
        event_id="example-event",
        registrations=(
            CartRegistration(
                id=id,
                old_data={},
                new_data={
                    "id": str(id),
                    "event_id": "example-event",
                    "date_created": "2020-01-01T00:00:00+00:00",
                    "state": "created",
                    "option_ids": ["attendee"],
                },
            ),
        ),
    )

    cart = CartEntity.create(cart_data)
    cart_id = cart.id
    await service.save_cart(cart)
    await db.commit()
    return cart_id


@pytest.mark.asyncio
async def test_get_cart(service: CartService, cart_id: str):
    res = await service.get_cart(cart_id)
    assert res.id == cart_id


@pytest.mark.asyncio
async def test_get_empty_cart(service: CartService):
    cart = await service.get_empty_cart("example-event")
    model = cart.get_cart_data_model()
    assert model.registrations == ()
