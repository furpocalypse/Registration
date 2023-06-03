import uuid

import pytest
from oes.registration.entities.registration import RegistrationEntity
from oes.registration.models.registration import Registration, RegistrationState
from oes.registration.util import get_now


def test_state_transition():
    reg = RegistrationEntity(
        version=1,
        state=RegistrationState.pending,
    )

    assert reg.complete()
    assert reg.state == RegistrationState.created
    assert reg.version == 2

    assert reg.complete() is False
    assert reg.version == 2

    assert reg.cancel()
    assert reg.state == RegistrationState.canceled
    assert reg.version == 2

    assert reg.cancel() is False
    assert reg.version == 2

    reg2 = RegistrationEntity(
        version=1,
        state=RegistrationState.pending,
    )

    assert reg2.cancel()
    assert reg2.version == 2
    assert reg2.state == RegistrationState.canceled

    with pytest.raises(ValueError):
        reg2.complete()


def test_get_model():
    reg = RegistrationEntity(
        id=uuid.uuid4(),
        state=RegistrationState.created,
        event_id="example",
        version=1,
        date_created=get_now(),
        option_ids={"test1"},
        extra_data={"extra": 123},
    )

    model = reg.get_model()
    assert model == Registration(
        id=reg.id,
        state=RegistrationState.created,
        event_id="example",
        version=1,
        date_created=reg.date_created,
        option_ids={"test1"},
        extra_data={"extra": 123},
    )

    # mutable properties should have been copied
    reg.extra_data["extra"] = 0
    reg.option_ids.add("test2")
    assert model.extra_data["extra"] == 123
    assert model.option_ids == {"test1"}


def test_update_from_model():
    id_ = uuid.uuid4()
    created = get_now()

    reg = RegistrationEntity(
        id=id_,
        state=RegistrationState.created,
        event_id="example",
        version=1,
        date_created=created,
        option_ids={"test1"},
        extra_data={
            "value1": 1,
            "value2": 2,
        },
    )

    model = Registration(
        id=uuid.uuid4(),
        state=RegistrationState.canceled,
        event_id="bad",
        version=123,
        date_created=get_now(),
        option_ids={"test2"},
        extra_data={
            "value2": 3,
            "value3": 3,
        },
    )

    reg.update_properties_from_model(model)

    # read-only fields should not have been copied
    assert reg.id == id_
    assert reg.date_created == created
    assert reg.event_id == "example"
    assert reg.version == 2
    assert reg.option_ids == {"test2"}

    # extra data should have been merged
    assert reg.extra_data == {
        "value1": 1,
        "value2": 3,
        "value3": 3,
    }


def test_display_name():
    r = RegistrationEntity()
    assert r.display_name == "Registration"

    r.email = "test@test.com"
    assert r.display_name == "test@test.com"

    r.last_name = "Lname"
    assert r.display_name == "Lname"

    r.first_name = "Fname"
    assert r.display_name == "Fname Lname"

    r.last_name = None
    assert r.display_name == "Fname"

    r.preferred_name = "Prefname"
    assert r.display_name == "Prefname"
