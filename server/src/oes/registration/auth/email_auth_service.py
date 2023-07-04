"""Email auth service."""
import asyncio
from inspect import iscoroutinefunction
from typing import Optional

from oes.registration.auth.entities import EmailAuthCodeEntity
from oes.registration.auth.models import EmailAuthCodeHookBody
from oes.registration.hook.models import HookConfig, HookEvent
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from oes.registration.serialization import get_converter


class EmailAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_auth_code_for_email(
            self, email: str
    ) -> Optional[EmailAuthCodeEntity]:
        """Return the :class:`EmailAuthCodeEntity` for an email."""
        q = (
            select(EmailAuthCodeEntity)
            .where(func.lower(EmailAuthCodeEntity.email) == email.lower())
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
        hook_config: HookConfig,
        email: str,
):
    """Create/update a :class:`EmailAuthCodeEntity` and invoke the hooks."""
    entity = await service.create_auth_code(email)
    if not entity:
        return

    body = EmailAuthCodeHookBody(
        email=email,
        code=entity.code,
        num_sent=entity.num_sent,
        attempts=entity.attempts,
        date_created=entity.date_created,
        date_expires=entity.date_expires,
    )
    body_dict = get_converter().unstructure(body)

    hooks = hook_config.get_by_event(HookEvent.email_auth_code)
    for hook in hooks:
        fn = hook.get_hook()
        if iscoroutinefunction(fn):
            await fn(body_dict)
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, fn, body_dict)
