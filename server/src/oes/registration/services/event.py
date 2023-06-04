"""Event service."""

from oes.registration.entities.event_stats import EventStatsEntity
from sqlalchemy.ext.asyncio import AsyncSession


class EventService:
    """Event service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_event_stats(self, id: str, *, lock: bool = False) -> EventStatsEntity:
        """Get the :class:`EventStatsEntity` for an event.

        Creates a new record if it doesn't exist.

        Args:
            id: The event ID.
            lock: Whether to lock the row.
        """
        entity = await self.db.get(EventStatsEntity, id, with_for_update=lock)
        if entity:
            return entity
        else:
            entity = EventStatsEntity(id=id)
            self.db.add(entity)
            await self.db.flush()
            return entity
