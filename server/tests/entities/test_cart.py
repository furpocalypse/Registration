import uuid

from oes.registration.entities.cart import CartEntity
from oes.registration.models.cart import CartData, CartRegistration


def test_create_cart_entity():
    id_ = uuid.uuid4()
    data = CartData(
        event_id="example-event",
        registrations=(
            CartRegistration(
                id=id_,
                old_data={
                    "a": 1,
                },
                new_data={
                    "a": 2,
                    "b": 2,
                },
                meta={"reg_meta": True},
            ),
        ),
        meta={"cart_meta": True},
    )

    hash_ = data.get_hash()

    entity = CartEntity.create(data)
    assert entity.id == hash_

    model = entity.get_cart_data_model()
    assert model == data
