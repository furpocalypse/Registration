from collections.abc import Sequence
from datetime import datetime
from typing import Optional

from oes.registration.entities.access_code import AccessCodeEntity, generate_code
from oes.registration.models.access_code import AccessCodeSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AccessCodeService:
    """Access code service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_access_code(
        self, code: str, *, lock: bool = False
    ) -> Optional[AccessCodeEntity]:
        """Get an access code.

        Args:
            code: The code.
            lock: Whether to lock the resource.
        """
        return await self.db.get(AccessCodeEntity, code, with_for_update=lock)

    async def create_access_code(
        self,
        event_id: str,
        name: Optional[str],
        expiration_date: datetime,
        settings: AccessCodeSettings,
    ):
        """Create an access code."""
        entity = AccessCodeEntity(
            code=generate_code(),
            event_id=event_id,
            name=name,
            date_expires=expiration_date,
            used=False,
        )
        entity.set_settings(settings)
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def list_access_codes(
        self, *, event_id: Optional[str] = None, page: int = 0, per_page: int = 50
    ) -> Sequence[AccessCodeEntity]:
        """List access codes."""
        q = select(AccessCodeEntity)

        if event_id:
            q = q.where(AccessCodeEntity.event_id == event_id)

        q = (
            q.order_by(AccessCodeEntity.date_created.desc())
            .offset(page * per_page)
            .limit(per_page)
        )

        res = await self.db.scalars(q)
        return res.all()

    async def delete_access_code(self, code: AccessCodeEntity):
        """Delete an access code."""
        await self.db.delete(code)
