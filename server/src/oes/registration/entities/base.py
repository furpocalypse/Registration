"""Base entity objects."""
import uuid
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from sqlalchemy import UUID as SqlUUID
from sqlalchemy import DateTime, MetaData, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, mapped_column

DEFAULT_MAX_STRING_LENGTH = 300
"""Default maximum length of a string."""

DEFAULT_MAX_ENUM_LENGTH = 16
"""Default length of an enum string value."""

DEFAULT_CASCADE = "save-update, merge, expunge"
"""Default relationship cascade configuration."""

DEFAULT_CASCADE_DELETE = "save-update, merge, expunge, delete"
"""Default relationship cascade configuration, with delete."""

DEFAULT_CASCADE_DELETE_ORPHAN = "save-update, merge, expunge, delete, delete-orphan"
"""Default relationship cascade configuration, with delete-orphan."""

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)

PKUUID = Annotated[
    UUID,
    mapped_column(
        SqlUUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4()
    ),
]
"""UUID primary key type."""

LongStr = Annotated[str, mapped_column(Text, nullable=True)]
"""Text type."""

JSONData = Annotated[
    dict[str, Any], mapped_column(JSONB, nullable=True, default=lambda: {})
]
"""JSON type."""


class Base(DeclarativeBase):
    """Entity base class."""

    metadata = metadata
    type_annotation_map = {
        UUID: SqlUUID(as_uuid=True),
        datetime: DateTime(timezone=True),
        str: String(DEFAULT_MAX_STRING_LENGTH),
    }


def import_entities():
    """Import all modules that contain entities."""
    from oes.registration.entities import access_code  # noqa
    from oes.registration.entities import auth  # noqa
    from oes.registration.entities import cart  # noqa
    from oes.registration.entities import checkout  # noqa
    from oes.registration.entities import event_stats  # noqa
    from oes.registration.entities import registration  # noqa
