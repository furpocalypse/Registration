"""Auth models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from attrs import frozen


class CredentialType(str, Enum):
    """Credential types."""

    refresh_token = "refresh_token"
    webauthn = "webauthn"


@frozen
class EmailAuthCodeHookBody:
    """Email auth code event data."""

    to: str
    code: str
    num_sent: int
    attempts: int
    date_created: datetime
    date_expires: datetime
