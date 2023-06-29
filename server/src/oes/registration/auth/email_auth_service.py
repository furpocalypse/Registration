"""Email auth service."""
import secrets
from datetime import timedelta
from typing import Optional

from oes.registration.auth.entities import AUTH_CODE_EXPIRATION_SEC, EmailAuthCodeEntity
from oes.registration.auth.models import EmailAuthCodeHookBody
from oes.registration.hook.service import HookSender
from oes.registration.util import get_now
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class EmailAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_auth_code_for_email(
        self, email: str
    ) -> Optional[EmailAuthCodeEntity]:
        """Return the :class:`EmailAuthCodeEntity` for an email."""
        q = (
            select(EmailAuthCodeEntity)
            .where(EmailAuthCodeEntity.email.lower() == email.lower())
            .with_for_update()
        )

        return await self.db.scalar(q)

    async def create_auth_code(self, email: str) -> Optional[EmailAuthCodeEntity]:
        """Create a new auth code for an email.

        Returns:
            A :class:`EmailAuthCodeEntity`, or ``None`` if the number of attempts has
            been exceeded.
        """

        entity = await self.get_auth_code_for_email(email)
        if entity is None:
            entity = EmailAuthCodeEntity(
                email=email,
                num_sent=0,
                attempts=0,
            )
            self.db.add(entity)
        elif not entity.can_send:
            return None

        new_code = entity.set_code()
        if new_code is None:
            return None

        await self.db.flush()

        return entity

    async def delete_code(self, entity: EmailAuthCodeEntity):
        """Delete the :class:`EmailAuthCodeEntity`."""
        await self.db.delete(entity)


async def send_auth_code(
    service: EmailAuthService,
    hook_sender: HookSender,
    email: str,
):
    entity = await service.create_auth_code(email)
    if not entity:
        return

    body = EmailAuthCodeHookBody(email)
