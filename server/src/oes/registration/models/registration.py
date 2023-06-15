"""Registration models."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID

from attrs import Factory, define, field, frozen
from cattrs import ClassValidationError, Converter


class RegistrationState(str, Enum):
    """The state of a registration."""

    pending = "pending"
    created = "created"
    canceled = "canceled"


@define(kw_only=True)
class Registration:
    """Registration model."""

    id: UUID
    state: RegistrationState
    event_id: str
    version: int
    date_created: datetime
    date_updated: Optional[datetime] = None

    number: Optional[int] = None
    option_ids: set[str] = field(default=Factory(lambda: set()))
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None

    extra_data: dict[str, Any] = {}


@define(kw_only=True)
class WritableRegistration:
    """Registration model comprising only updatable fields."""

    number: Optional[int] = None
    option_ids: set[str] = field(default=Factory(lambda: set()))
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None

    extra_data: dict[str, Any] = {}


@define(kw_only=True)
class SelfServiceRegistration:
    """Registration model shown in self-service pages."""

    id: UUID
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None


@frozen
class RegistrationUpdatedEvent:
    """The body sent with a :class:`HookEvent.registration_updated` event."""

    old_data: Registration
    new_data: Registration


READ_ONLY_FIELDS = frozenset(
    {
        "id",
        "state",
        "event_id",
        "version",
        "date_created",
        "date_updated",
    }
)
"""Field names of read-only fields."""

STANDARD_FIELDS = frozenset(
    {
        "number",
        "option_ids",
        "email",
        "first_name",
        "last_name",
        "preferred_name",
    }
)
"""The standard updatable fields."""


def structure_writable_registration(
    converter: Converter, value: Any
) -> WritableRegistration:
    """Structure the writable fields of a registration."""
    if not isinstance(value, dict):
        raise TypeError(f"Invalid type: {value}")

    attr_dict = {}
    extra = {}
    for k, v in value.items():
        if k in STANDARD_FIELDS:
            attr_dict[k] = v
        elif k not in READ_ONLY_FIELDS:
            extra[k] = v
        else:
            # Otherwise, omit the field
            pass

    try:
        return converter.structure_attrs_fromdict(
            {
                **attr_dict,
                "extra_data": extra,
            },
            WritableRegistration,
        )
    except Exception as e:
        raise ClassValidationError("Invalid Registration", [e], Registration)


def structure_registration(converter: Converter, value: Any) -> Registration:
    """Structure all fields of a registration."""
    if not isinstance(value, dict):
        raise TypeError(f"Invalid type: {value}")

    attr_dict = {}
    extra = {}
    for k, v in value.items():
        if k in READ_ONLY_FIELDS or k in STANDARD_FIELDS:
            attr_dict[k] = v
        else:
            extra[k] = v

    try:
        return converter.structure_attrs_fromdict(
            {
                **attr_dict,
                "extra_data": extra,
            },
            Registration,
        )
    except Exception as e:
        raise ClassValidationError("Invalid Registration", [e], Registration)


def unstructure_registration(
    converter: Converter, value: Union[Registration, WritableRegistration]
) -> dict[str, Any]:
    """Unstructure a registration."""
    data = converter.unstructure_attrs_asdict(value)
    final_data = {}
    for k, v in data["extra_data"].items():
        if v is not None:
            final_data[k] = v

    for k, v in data.items():
        if k != "extra_data" and v is not None:
            final_data[k] = v

    return final_data
