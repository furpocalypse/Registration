"""Event stats."""
from oes.registration.entities.base import DEFAULT_MAX_STRING_LENGTH, Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class EventStatsEntity(Base):
    """Event stats."""

    __tablename__ = "event_stats"

    id: Mapped[str] = mapped_column(String(DEFAULT_MAX_STRING_LENGTH), primary_key=True)
    """The event ID."""

    next_number: Mapped[int] = mapped_column(default=1)
    """The next registration number."""
