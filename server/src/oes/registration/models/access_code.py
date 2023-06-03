"""Access code models."""
from collections.abc import Sequence
from typing import Any

from attrs import frozen


@frozen
class AccessCodeSettings:
    """Access code settings."""

    interview_ids: Sequence[str] = ()
    """The interview IDs to allow."""

    change_interview_ids: Sequence[str] = ()
    """The change interview IDs to allow."""

    initial_data: dict[str, Any] = {}
    """The data to merge into the interview's initial data."""
