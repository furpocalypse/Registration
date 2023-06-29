"""Auth entities."""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from blacksheep.messages import datetime
from oes.registration.auth.models import CredentialType
from oes.registration.entities.base import (
    DEFAULT_CASCADE_DELETE_ORPHAN,
    PKUUID,
    Base,
    JSONData,
)
from oes.registration.util import get_now
from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

CREDENTIAL_TYPE_LEN = 32
CREDENTIAL_ID_MAX_LEN = 1024
EMAIL_MAX_LEN = 254
AUTH_CODE_LEN = 6
AUTH_CODE_MAX_LEN = 12
AUTH_CODE_MAX_NUM_SENT = 10
AUTH_CODE_MAX_ATTEMPTS = 10
AUTH_CODE_EXPIRATION_SEC = 1800

if TYPE_CHECKING:
    from oes.registration.entities.registration import RegistrationEntity

_digits = "0123456789"


class AccountEntity(Base):
    """Account entity."""

    __tablename__ = "account"

    id: Mapped[PKUUID]
    """The account ID."""

    email: Mapped[Optional[str]]
    """The email associated with this account."""

    credentials: Mapped[list[CredentialEntity]] = relationship(
        back_populates="account",
        cascade=DEFAULT_CASCADE_DELETE_ORPHAN,
    )
    """:class:`CredentialEntity` instances associated with this account."""

    registrations: Mapped[list[RegistrationEntity]] = relationship(
        "RegistrationEntity",
        secondary="registration_account",
        back_populates="accounts",
    )

    def __repr__(self):
        return (
            f"<Account id={self.id} "
            + (f"email={self.email} " if self.email else "")
            + ">"
        )

    def revoke_refresh_tokens(self):
        """Remove/revoke all refresh tokens for this account."""
        to_remove = [
            c for c in self.credentials if c.type == CredentialType.refresh_token
        ]

        for c in to_remove:
            self.credentials.remove(c)


class CredentialEntity(Base):
    """Credential entity."""

    __tablename__ = "credential"

    id: Mapped[str] = mapped_column(String(CREDENTIAL_ID_MAX_LEN), primary_key=True)
    """The credential ID."""

    account_id: Mapped[UUID] = mapped_column(ForeignKey("account.id"))
    """The account ID."""

    type: Mapped[CredentialType] = mapped_column(String(CREDENTIAL_TYPE_LEN))
    """The type of credential."""

    date_created: Mapped[datetime]
    """The date the credential was created."""

    date_updated: Mapped[Optional[datetime]]
    """The date the credential was updated."""

    date_last_used: Mapped[Optional[datetime]]
    """The date the credential was last used."""

    date_expires: Mapped[Optional[datetime]]
    """The date the credential expires."""

    data: Mapped[JSONData]
    """The credential data."""

    account: Mapped[AccountEntity] = relationship(back_populates="credentials")
    """The :class:`AccountEntity` the credential is for."""


class EmailAuthCodeEntity(Base):
    """Entity for email auth codes."""

    __tablename__ = "email_auth"

    __table_args__ = (
        Index(
            "uq_email_auth_lower_email",
            func.lower("email"),
            unique=True,
        ),
    )

    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LEN), primary_key=True)
    """The email address."""

    date_created: Mapped[datetime]
    """The date the auth code was created."""

    date_expires: Mapped[datetime]
    """The date the auth code expires."""

    num_sent: Mapped[int]
    """The number of sent codes."""

    attempts: Mapped[int]
    """Number of attempts."""

    code: Mapped[Optional[str]] = mapped_column(String(AUTH_CODE_MAX_LEN))
    """The auth code."""

    def get_is_expired(self, *, now: Optional[datetime] = None) -> bool:
        """Return whether the code is expired."""
        now = now if now is not None else get_now()
        return now >= self.date_expires

    def get_is_usable(self, *, now: Optional[datetime] = None) -> bool:
        """Checks that the code is not expired and the max attempts not exceeded."""
        return self.attempts < AUTH_CODE_MAX_ATTEMPTS and not self.get_is_expired(
            now=now
        )

    @property
    def can_send(self) -> bool:
        """Whether a code can be sent."""
        return (
            self.num_sent < AUTH_CODE_MAX_NUM_SENT
            and self.attempts < AUTH_CODE_MAX_ATTEMPTS
        )

    def set_code(self, *, now: Optional[datetime] = None) -> Optional[str]:
        """Create and set a code for this entity.

        Sets the code, created/expiration date, and increments the number of codes.

        Args:
            now: The current time.

        Returns:
            The new code, or ``None`` if the number of attempts were exceeded.
        """
        if not self.can_send:
            return None
        self.code = self.generate_code()
        now = now if now is not None else get_now()
        self.date_created = now
        self.date_expires = now + timedelta(seconds=AUTH_CODE_EXPIRATION_SEC)
        self.num_sent += 1
        return self.code

    def validate(self, code: str, *, now: Optional[datetime] = None) -> bool:
        """Return whether a code is valid."""
        return self.get_is_usable(now=now) and self.code and code == self.code

    @classmethod
    def generate_code(cls) -> str:
        """Generate an auth code."""
        return "".join(secrets.choice(_digits) for _ in range(AUTH_CODE_LEN))


import oes.registration.entities.registration  # noqa
