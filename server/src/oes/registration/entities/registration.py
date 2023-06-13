"""Registration entities."""
from __future__ import annotations

import copy
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from oes.registration.entities.base import (
    DEFAULT_MAX_ENUM_LENGTH,
    PKUUID,
    Base,
    JSONData,
)
from oes.registration.entities.event_stats import EventStatsEntity
from oes.registration.hook.models import HookEvent
from oes.registration.hook.service import HookSender
from oes.registration.log import AuditLogType, audit_log
from oes.registration.models.registration import (
    Registration,
    RegistrationState,
    WritableRegistration,
)
from oes.registration.serialization import get_converter
from oes.registration.util import get_now, merge_dict
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from oes.registration.entities.auth import AccountEntity
    from oes.registration.models.cart import CartRegistration, InvalidChangeError


class RegistrationEntity(Base):
    """Registration entity."""

    __tablename__ = "registration"

    __table_args__ = (
        Index(
            "ix_registration_extra_data_jsonb",
            "extra_data",
            postgresql_using="gin",
            postgresql_ops={
                "extra_data": "jsonb_path_ops",
            },
        ),
    )

    id: Mapped[PKUUID]
    """The registration ID."""

    state: Mapped[RegistrationState] = mapped_column(
        String(DEFAULT_MAX_ENUM_LENGTH),
        default=RegistrationState.pending,
    )
    """The registration state."""

    event_id: Mapped[str]
    """The ID of the event this registration belongs to."""

    version: Mapped[int] = mapped_column(default=1)
    """The version of this record."""

    date_created: Mapped[datetime] = mapped_column(default=lambda: get_now())
    """The date the registration was created."""

    date_updated: Mapped[Optional[datetime]]
    """The date the registration was updated."""

    # Standard fields

    number: Mapped[Optional[int]]
    """The registration number."""

    option_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=True, default=lambda: []
    )
    """The registration option IDs."""

    email: Mapped[Optional[str]]
    """The registration email."""

    first_name: Mapped[Optional[str]]
    """The registration first (given) name."""

    last_name: Mapped[Optional[str]]
    """The registration last (family) name."""

    preferred_name: Mapped[Optional[str]]
    """The registration preferred name."""

    extra_data: Mapped[JSONData]
    """Additional data."""

    accounts: Mapped[list[AccountEntity]] = relationship(
        "AccountEntity",
        secondary="registration_account",
        back_populates="registrations",
    )
    """Accounts associated with this registration."""

    _updated: bool = False

    @property
    def display_name(self) -> str:
        """A display name for the registration."""
        if self.preferred_name:
            return self.preferred_name
        elif self.first_name or self.last_name:
            names = [self.first_name, self.last_name]
            return " ".join(n for n in names if n)
        elif self.email:
            return self.email
        else:
            return "Registration"

    def __repr__(self):
        return (
            "<Registration "
            f"id={self.id} "
            + (f"number={self.number} " if self.number is not None else "")
            + f"first_name={self.first_name} "
            f"last_name={self.last_name} "
            f"preferred_name={self.preferred_name} "
            f"email={self.email}"
            ">"
        )

    def _update_properties_from_model(
        self, v: Union[Registration, WritableRegistration]
    ):
        self.number = v.number
        self.option_ids = set(v.option_ids)
        self.email = v.email
        self.first_name = v.first_name
        self.last_name = v.last_name
        self.preferred_name = v.preferred_name
        extra_data = copy.deepcopy(self.extra_data) if self.extra_data else {}
        merge_dict(extra_data, v.extra_data)
        self.extra_data = extra_data

    def update_properties_from_model(
        self, v: Union[Registration, WritableRegistration]
    ):
        """Update the entity's properties from a model.

        Only copies the writable properties.

        Updates the ``date_updated`` and ``version`` automatically.
        """
        self._update_properties_from_model(v)
        self.mark_updated()

    def get_model(self) -> Registration:
        """Get a :class:`Registration` model from this entity."""
        return Registration(
            id=self.id,
            state=self.state,
            event_id=self.event_id,
            version=self.version,
            date_created=self.date_created,
            date_updated=self.date_updated,
            number=self.number,
            option_ids=set(self.option_ids),
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            preferred_name=self.preferred_name,
            extra_data=copy.deepcopy(self.extra_data) if self.extra_data else {},
        )

    def mark_updated(self) -> None:
        """Set ``date_updated`` and increment the ``version``.

        Only happens once per commit.
        """
        if not self._updated:
            self._updated = True
            self.version += 1
            self.date_updated = get_now()

    def complete(self) -> bool:
        """Set the registration to ``created``.

        Returns:
            Whether a change was made.
        """
        if self.state == RegistrationState.created:
            return False

        if self.state != RegistrationState.pending:
            raise ValueError("Registration is not pending")

        self.state = RegistrationState.created
        self.date_created = get_now()
        self.mark_updated()
        audit_log.bind(type=AuditLogType.registration_create).success(
            "Registration {registration} marked as created", registration=self
        )
        return True

    def cancel(self) -> bool:
        """Set the registration to ``canceled``.

        Returns:
            Whether a change was made.
        """
        if self.state != RegistrationState.canceled:
            self.state = RegistrationState.canceled
            self.mark_updated()
            audit_log.bind(type=AuditLogType.registration_cancel).success(
                "Registration {registration} marked as canceled", registration=self
            )
            return True
        else:
            return False

    @classmethod
    def create_from_cart(
        cls, cart_registration: CartRegistration
    ) -> RegistrationEntity:
        """Create a :class:`RegistrationEntity` from cart data.

        Args:
            cart_registration: The :class:`CartRegistration`.

        Returns:
            The created entity.
        """
        reg = get_converter().structure(cart_registration.new_data, Registration)
        entity = cls(
            id=reg.id,
            event_id=reg.event_id,
            state=reg.state,
            version=reg.version,
            date_created=get_now(),
            accounts=[],
        )
        entity._update_properties_from_model(reg)

        return entity

    def validate_changes_from_cart(self, cart_registration: CartRegistration) -> bool:
        """Validate that the changes in the cart can be applied.

        Args:
            cart_registration: The :class:`CartRegistration`.

        Returns:
            Whether the cart changes are valid.
        """
        cur_version = self.version
        cart_cur_version = cart_registration.old_data.get("version")
        cur_state = self.state
        cart_next_state = cart_registration.new_data.get("state")

        if cart_cur_version != cur_version:
            return False

        if (
            cart_next_state == RegistrationState.pending
            and cur_state != RegistrationState.pending
        ):
            return False

        return True

    async def apply_changes_from_cart(
        self,
        cart_registration: CartRegistration,
        hook_sender: HookSender,
    ):
        """Apply changes from a :class:`CartRegistration`.

        Raises:
            InvalidChangeError: if the registration is out of date.
        """
        if not self.validate_changes_from_cart(cart_registration):
            raise InvalidChangeError(cart_registration.id)

        cart_next_state = cart_registration.new_data.get("state")

        # Extract the writable attributes
        writable = get_converter().structure(
            cart_registration.new_data, WritableRegistration
        )

        # Update
        self.update_properties_from_model(writable)

        # Update the state
        if cart_next_state == RegistrationState.created:
            self.complete() and await hook_sender.schedule_hooks_for_event(
                HookEvent.registration_created,
                get_converter().unstructure(self.get_model()),
            )
        elif cart_next_state == RegistrationState.canceled:
            self.cancel() and await hook_sender.schedule_hooks_for_event(
                HookEvent.registration_canceled,
                get_converter().unstructure(self.get_model()),
            )

    def assign_number(self, event_stats: EventStatsEntity) -> int:
        """Assign a registration number.

        Updates the ``next_number``. Does nothing if a number is already assigned.

        Args:
            event_stats: The :class:`EventStatsEntity` to track the next number.

        Returns:
            The assigned number.
        """
        if self.number is not None:
            return self.number

        audit_log.bind(type=AuditLogType.registration_update).success(
            "Registration {registration} assigned number {}",
            event_stats.next_number,
            registration=self,
        )
        self.number = event_stats.next_number
        event_stats.next_number += 1
        self.mark_updated()
        return self.number


class RegistrationAccount(Base):
    """Entity to map registrations to accounts."""

    __tablename__ = "registration_account"

    registration_id: Mapped[UUID] = mapped_column(
        ForeignKey("registration.id"), primary_key=True
    )
    """The registration ID."""

    account_id: Mapped[UUID] = mapped_column(ForeignKey("account.id"), primary_key=True)
    """The account ID."""
