"""Hook database entities."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from oes.registration.entities.base import PKUUID, Base, JSONData
from oes.registration.hook.models import NUM_RETRIES, RETRY_SECONDS, HookConfigEntry
from oes.registration.serialization import get_config_converter
from oes.registration.util import get_now
from sqlalchemy.orm import Mapped


class HookLogEntity(Base):
    """Hook log entity."""

    __tablename__ = "hook_log"

    id: Mapped[PKUUID]
    """Hook ID."""

    attempts: Mapped[int]
    """Number of attempts."""

    retry_at: Mapped[Optional[datetime]]
    """The retry time."""

    config: Mapped[JSONData]
    """Hook config."""

    body: Mapped[JSONData]
    """Hook data body."""

    @classmethod
    def create(
        cls, hook_config: HookConfigEntry, body: dict[str, Any]
    ) -> HookLogEntity:
        """Create a hook log entity."""
        config = get_config_converter().unstructure(hook_config)

        return HookLogEntity(
            id=uuid.uuid4(),
            attempts=0,
            retry_at=None,
            config=config,
            body=body,
        )

    def get_config_entry(self) -> HookConfigEntry:
        """Get the :class:`HookConfigEntry` object."""
        return get_config_converter().structure(self.config, HookConfigEntry)

    def get_is_retryable(self, *, now: Optional[datetime] = None) -> bool:
        """Get whether this hook is eligible for retry."""
        now = now if now is not None else get_now()
        return self.retry_at is not None and self.retry_at <= now

    def update_attempts(self) -> Optional[datetime]:
        """Update the number of attempts and set the next retry time."""
        n_attempts = self.attempts
        self.attempts += 1
        if self.attempts > NUM_RETRIES:
            self.retry_at = None
            return None

        delay = RETRY_SECONDS[n_attempts]
        now = get_now()
        self.retry_at = now + timedelta(seconds=delay)

        return self.retry_at
