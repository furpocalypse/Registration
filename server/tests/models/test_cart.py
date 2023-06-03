import uuid

import pytest
from oes.registration.entities.registration import RegistrationEntity
from oes.registration.models.cart import (
    CART_HASH_SIZE,
    CartData,
    CartError,
    CartRegistration,
)
from oes.registration.models.registration import Registration, RegistrationState
from oes.registration.util import get_now


def test_hash_cart():
    id_1 = uuid.uuid4()
    id_2 = uuid.uuid4()
    c1 = CartData(
        event_id="example-event",
        registrations=(
            CartRegistration(
                id=id_1,
            ),
        ),
    )
    c2 = CartData(
        event_id="example-event",
        registrations=(
            CartRegistration(
                id=id_2,
            ),
        ),
    )
    c3 = CartData(
        event_id="example-event",
        registrations=(
            CartRegistration(
                id=id_1,
            ),
        ),
    )

    a = c1.get_hash()
    b = c2.get_hash()
    c = c3.get_hash()

    assert a == c
    assert b != c
    assert len(a) == CART_HASH_SIZE


def test_create_cart_registration():
    id = uuid.uuid4()
    dc = get_now()

    a = Registration(
        id=id,
        state=RegistrationState.pending,
        event_id="example",
        version=1,
        date_created=dc,
        option_ids=set(),
    )

    b = Registration(
        id=id,
        state=RegistrationState.created,
        event_id="example",
        version=2,
        date_created=dc,
        option_ids={"opt1"},
    )

    res = CartRegistration.create(a, b, meta={"meta": True})

    assert res == CartRegistration(
        id=id,
        old_data={
            "id": id,
            "state": RegistrationState.pending,
            "event_id": "example",
            "version": 1,
            "date_created": dc,
            "option_ids": set(),
        },
        new_data={
            "id": id,
            "state": RegistrationState.created,
            "event_id": "example",
            "version": 2,
            "date_created": dc,
            "option_ids": {"opt1"},
        },
        meta={"meta": True},
    )


def test_create_cart_registration_none():
    id = uuid.uuid4()
    dc = get_now()

    e = RegistrationEntity(
        id=id,
        state=RegistrationState.created,
        event_id="example",
        version=1,
        date_created=dc,
        option_ids=["opt1"],
        extra_data={},
    )

    res = CartRegistration.create(None, e)

    assert res == CartRegistration(
        id=id,
        old_data={},
        new_data={
            "id": id,
            "state": RegistrationState.created,
            "event_id": "example",
            "version": 1,
            "date_created": dc,
            "option_ids": {"opt1"},
        },
    )


def test_create_cart_add_remove():
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    dc = get_now()

    r1 = Registration(
        id=id1,
        state=RegistrationState.created,
        event_id="example-event",
        version=1,
        date_created=dc,
        option_ids={"opt1"},
    )
    cr1 = CartRegistration.create(None, r1, submission_id="s1")

    r2 = Registration(
        id=id2,
        state=RegistrationState.created,
        event_id="example-event",
        version=1,
        date_created=dc,
        option_ids={"opt1"},
    )
    cr2 = CartRegistration.create(None, r2, submission_id="s2")

    empty = CartData(event_id="example-event")

    with_r1 = empty.add_registration(cr1)
    assert with_r1 != empty
    assert len(with_r1.registrations) == 1
    assert with_r1.registrations[0] == cr1

    with_r2 = with_r1.add_registration(cr2)
    assert len(with_r2.registrations) == 2
    assert tuple(with_r2.registrations) == (cr1, cr2)

    r2_without_r1 = with_r2.remove_registration(cr1)
    assert len(r2_without_r1.registrations) == 1
    assert r2_without_r1.registrations[0] == cr2

    assert with_r2.remove_registration(cr2) == with_r1

    assert r2_without_r1.remove_registration(cr2) == empty

    # Removing non-existing item is a no-op
    assert r2_without_r1.remove_registration(cr1) == r2_without_r1

    # Remove by ID
    assert with_r2.remove_registration(id2) == with_r1


def test_cart_duplicate_registrations():
    id1 = uuid.uuid4()
    dc = get_now()

    r1 = Registration(
        id=id1,
        state=RegistrationState.created,
        event_id="example-event",
        version=1,
        date_created=dc,
        option_ids={"opt1"},
    )

    r2 = Registration(
        id=id1,
        state=RegistrationState.created,
        event_id="example-event",
        version=1,
        date_created=dc,
        option_ids={"opt1"},
    )

    cr1 = CartRegistration.create(None, r1)

    cart = CartData(event_id="example-event")

    cart = cart.add_registration(cr1)

    cr2 = CartRegistration.create(None, r2)

    with pytest.raises(CartError):
        cart.add_registration(cr2)


def test_cart_duplicate_submission():
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    dc = get_now()

    r1 = Registration(
        id=id1,
        state=RegistrationState.created,
        event_id="example-event",
        version=1,
        date_created=dc,
        option_ids={"opt1"},
    )

    r2 = Registration(
        id=id2,
        state=RegistrationState.created,
        event_id="example-event",
        version=1,
        date_created=dc,
        option_ids={"opt1"},
    )

    cr1 = CartRegistration.create(None, r1, submission_id="s1")

    cart = CartData(event_id="example-event")

    cart = cart.add_registration(cr1)

    cr2 = CartRegistration.create(None, r2, submission_id="s1")

    with pytest.raises(CartError):
        cart.add_registration(cr2)


def test_cart_event_id_matches():
    id = uuid.uuid4()
    dc = get_now()

    reg = Registration(
        id=id,
        state=RegistrationState.created,
        event_id="example",
        version=1,
        date_created=dc,
        option_ids={"opt1"},
    )

    cart = CartData(event_id="example2")

    cr = CartRegistration.create(None, reg)

    with pytest.raises(CartError):
        cart.add_registration(cr)


def test_validate_changes():
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    id3 = uuid.uuid4()
    dc = get_now()

    reg1 = Registration(
        id=id1,
        state=RegistrationState.pending,
        event_id="example-event",
        version=5,
        date_created=dc,
        option_ids={"opt1"},
    )

    reg1_new = Registration(
        id=id1,
        state=RegistrationState.created,
        event_id="example-event",
        version=6,
        date_created=dc,
        option_ids={"opt1"},
    )

    reg2 = Registration(
        id=id2,
        state=RegistrationState.pending,
        event_id="example-event",
        version=5,
        date_created=dc,
        option_ids={"opt1"},
    )

    reg2_new = Registration(
        id=id2,
        state=RegistrationState.created,
        event_id="example-event",
        version=6,
        date_created=dc,
        option_ids={"opt1"},
    )

    reg2_cur = Registration(
        id=id2,
        state=RegistrationState.pending,
        event_id="example-event",
        version=6,
        date_created=dc,
        option_ids={"opt2"},
    )

    reg3 = Registration(
        id=id3,
        state=RegistrationState.created,
        event_id="example-event",
        version=1,
        date_created=dc,
        option_ids={"opt1"},
    )

    cart = CartData(
        event_id="example-event",
        registrations=(
            CartRegistration.create(reg1, reg1_new),
            CartRegistration.create(reg2, reg2_new),
            CartRegistration.create(None, reg3),
        ),
    )

    bad_ids = cart.validate_changes_apply([reg1, reg2_cur])
    assert bad_ids == [reg2.id]
