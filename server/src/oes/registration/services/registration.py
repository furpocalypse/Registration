"""Registration service."""
from collections.abc import Iterable, Sequence
from typing import Optional
from uuid import UUID

from oes.registration.entities.auth import AccountEntity
from oes.registration.entities.event_stats import EventStatsEntity
from oes.registration.entities.registration import RegistrationEntity
from oes.registration.log import AuditLogType, audit_log
from oes.registration.models.event import Event, EventInterviewOption
from oes.registration.models.registration import (
    RegistrationState,
    SelfServiceRegistration,
)
from oes.registration.serialization import get_converter
from oes.registration.services.auth import AuthService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, selectinload


class RegistrationService:
    """Registration service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_registration(self, registration: RegistrationEntity):
        """Create a new registration entity."""
        self.db.add(registration)
        await self.db.flush()

        if registration.state == RegistrationState.created:
            audit_log.bind(type=AuditLogType.registration_create).success(
                "Registration {registration} created", registration=registration
            )
        elif registration.state == RegistrationState.pending:
            audit_log.bind(type=AuditLogType.registration_create_pending).success(
                "Registration {registration} created in pending state",
                registration=registration,
            )

    async def get_registration(
        self, id: UUID, *, lock: bool = False, include_accounts: bool = False
    ) -> Optional[RegistrationEntity]:
        """Get a :class:`RegistrationEntity` by ID.

        Args:
            id: The registration ID.
            lock: Whether to lock the row.
            include_accounts: Include related :class:`AccountEntity` rows.
        """
        opts = []

        if include_accounts:
            opts.append(selectinload(RegistrationEntity.accounts))

        return await self.db.get(
            RegistrationEntity, id, with_for_update=lock, options=opts
        )

    async def get_registrations(
        self, ids: Iterable[UUID], *, lock: bool = False
    ) -> Sequence[RegistrationEntity]:
        """Get multiple registrations by ID.

        Args:
            ids: The IDs.
            lock: Whether to lock the rows.
        """
        q = (
            select(RegistrationEntity)
            .where(RegistrationEntity.id.in_(list(ids)))
            .order_by(RegistrationEntity.id)
        )

        if lock:
            q = q.with_for_update()

        res = await self.db.execute(q)
        return res.scalars().all()

    async def list_registrations(
        self, *, page: int = 0, per_page: int = 50
    ) -> Sequence[RegistrationEntity]:
        """Search for :class:`RegistrationEntity`."""
        q = (
            select(RegistrationEntity)
            .order_by(RegistrationEntity.date_created.desc())
            .offset(page * per_page)
            .limit(per_page)
        )

        res = await self.db.execute(q)
        return res.scalars().all()

    async def list_self_service_registrations(
        self,
        account_id: UUID,
        event_id: Optional[str] = None,
    ) -> Sequence[RegistrationEntity]:
        """List self-service registrations."""
        q = (
            select(RegistrationEntity)
            .join(RegistrationEntity.accounts)
            .where(AccountEntity.id == account_id)
        )

        if event_id is not None:
            q = q.where(RegistrationEntity.event_id == event_id)

        q = q.where(RegistrationEntity.state == RegistrationState.created)

        q = q.order_by(RegistrationEntity.date_created)

        q = q.options(contains_eager(RegistrationEntity.accounts))
        res = await self.db.execute(q)
        return res.unique().scalars().all()


def render_self_service_registration(
    event: Event, registration: RegistrationEntity
) -> SelfServiceRegistration:
    """Get a :class:`SelfServiceRegistration` model from an entity."""
    model = registration.get_model()
    event_dict = get_converter().unstructure(event)
    registration_dict = get_converter().unstructure(model)

    context = {
        "event": event_dict,
        "registration": {
            "display_name": registration.display_name,
            **registration_dict,
        },
    }

    result = SelfServiceRegistration(
        id=model.id,
        title=event.display_options.registration.title.render(**context),
        subtitle=event.display_options.registration.subtitle.render(**context),
        description=event.display_options.registration.description.render(**context),
    )

    return result


def get_allowed_add_interviews(event: Event) -> list[EventInterviewOption]:
    """Get the add interviews allowed for a registration."""
    event_dict = get_converter().unstructure(event)

    context = {
        "event": event_dict,
    }

    return [
        interview
        for interview in event.add_interviews
        if interview.when_matches(**context)
    ]


def get_allowed_change_interviews(
    event: Event, registration: RegistrationEntity
) -> list[EventInterviewOption]:
    """Get the change interviews allowed for a registration."""
    model = registration.get_model()
    event_dict = get_converter().unstructure(event)
    registration_dict = get_converter().unstructure(model)

    context = {
        "event": event_dict,
        "registration": {
            "display_name": registration.display_name,
            **registration_dict,
        },
    }

    return [
        interview
        for interview in event.change_interviews
        if interview.when_matches(**context)
    ]


def assign_registration_numbers(
    event_stats: EventStatsEntity, registrations: Iterable[RegistrationEntity]
):
    """Assign registration numbers.

    Skips registrations that are not in the ``created`` state.

    Args:
        event_stats: The :class:`EventStatsEntity` tracking the next number.
        registrations: The registrations to update.
    """
    for reg in registrations:
        if reg.event_id != event_stats.id:
            raise ValueError("Event ID does not match")
        if reg.state == RegistrationState.created:
            reg.assign_number(event_stats)


async def add_account_to_registration(
    account_id: UUID,
    registration: RegistrationEntity,
    auth_service: AuthService,
):
    """Associate an account with a registration."""
    account = await auth_service.get_account(account_id)
    if account:
        registration.accounts.append(account)
