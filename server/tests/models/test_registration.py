import json
import uuid

from oes.registration.models.registration import (
    Registration,
    RegistrationState,
    WritableRegistration,
)
from oes.registration.serialization import get_converter
from oes.registration.util import get_now


def test_structure():
    reg = Registration(
        id=uuid.uuid4(),
        state=RegistrationState.created,
        event_id="example",
        version=1,
        date_created=get_now(),
        number=100,
        option_ids={"test"},
        email="test@test.com",
        first_name="Example",
        last_name="Person",
        extra_data={
            "value1": 1,
            "value2": True,
        },
    )

    data = get_converter().dumps(reg)
    loaded_data = json.loads(data)

    assert loaded_data == dict(
        id=str(reg.id),
        state="created",
        event_id="example",
        version=1,
        date_created=reg.date_created.isoformat(),
        number=100,
        option_ids=["test"],
        email="test@test.com",
        first_name="Example",
        last_name="Person",
        value1=1,
        value2=True,
    )

    unstructured = get_converter().structure(loaded_data, Registration)
    assert unstructured == reg


def test_structure_read_only():
    data = {
        "id": "ignore",
        "state": "pending",
        "version": 10,
        "number": 100,
        "option_ids": ["test1", "test2", "test1"],
        "email": "test@test.com",
        "last_name": "Lastname",
        "extra1": {"value": True},
    }

    loaded = get_converter().structure(data, WritableRegistration)

    assert loaded == WritableRegistration(
        number=100,
        option_ids={"test1", "test2"},
        email="test@test.com",
        last_name="Lastname",
        extra_data={"extra1": {"value": True}},
    )
