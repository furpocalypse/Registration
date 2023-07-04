"""User module."""
from typing import Optional
from uuid import UUID

from attrs import frozen


@frozen
class User:
    """A user."""

    id: UUID
    """The user/account ID."""

    email: Optional[str] = None
    """The user's email."""
