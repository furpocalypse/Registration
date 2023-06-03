"""Access code entities."""
import secrets
from datetime import datetime
from typing import Optional

from oes.registration.entities.base import Base, JSONData
from oes.registration.models.access_code import AccessCodeSettings
from oes.registration.serialization import get_converter
from oes.registration.util import get_now
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

ACCESS_CODE_MAX_LEN = 36
"""Max length of an access code"""


class AccessCodeEntity(Base):
    """Access code entity."""

    __tablename__ = "access_code"

    code: Mapped[str] = mapped_column(String(ACCESS_CODE_MAX_LEN), primary_key=True)
    """The code."""

    event_id: Mapped[str]
    """The event ID."""

    date_created: Mapped[datetime] = mapped_column(default=lambda: get_now())
    """The date the code was created."""

    date_expires: Mapped[datetime]
    """The expiration date."""

    name: Mapped[Optional[str]]
    """Name for the access code."""

    used: Mapped[bool]
    """Whether the code is marked as used."""

    data: Mapped[JSONData]
    """The access code settings."""

    def get_settings(self) -> AccessCodeSettings:
        """Get the :class:`AccessCodeSettings` for this code."""
        return get_converter().structure(self.data or {}, AccessCodeSettings)

    def set_settings(self, settings: AccessCodeSettings):
        """Set the settings."""
        self.data = get_converter().unstructure(settings)

    def check_valid(self, *, now: Optional[datetime] = None) -> bool:
        """Check if the access code is valid.

        Checks the expiration date and ``used`` flag.

        Args:
            now: The current time.

        Returns:
            Whether the code is valid.
        """
        now = now if now is not None else get_now()
        return now < self.date_expires and not self.used


# TODO: placeholder for now, investigate different options
_code_chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_code() -> str:
    """Generate a code."""
    return "".join(secrets.choice(_code_chars) for _ in range(12))
