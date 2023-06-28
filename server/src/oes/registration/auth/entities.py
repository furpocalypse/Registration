"""Auth entities."""
from __future__ import annotations

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
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

CREDENTIAL_TYPE_LEN = 32
CREDENTIAL_ID_MAX_LEN = 1024

if TYPE_CHECKING:
    from oes.registration.entities.registration import RegistrationEntity


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
