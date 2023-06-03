"""Config models."""
from collections.abc import Sequence
from typing import Any, NewType, Optional

from attrs import field, frozen, validators


@frozen
class DatabaseConfig:
    url: str = field(repr=False)
    """The database URL."""


@frozen
class AuthConfig:
    signing_key: str = field(repr=False)
    """The token signing key."""

    allowed_origins: Sequence[str]
    """The allowed origins."""

    allowed_auth_origins: Sequence[str]
    """Origins which may use first-party auth endpoints."""

    name: str
    """The name of this service."""


PaymentServiceConfig = dict[str, Any]


@frozen
class PaymentConfig:
    currency: str = "USD"
    """The currency code."""

    services: Optional[dict[str, PaymentServiceConfig]] = {}
    """Per-service payment config."""


Base64Bytes = NewType("Base64Bytes", bytes)
"""Bytes encoded as a base64 string."""


@frozen
class InterviewConfig:
    """Interview config."""

    encryption_key: Base64Bytes = field(
        repr=False, validator=[validators.min_len(32), validators.max_len(32)]
    )
    """The encryption key used with the interview service."""

    update_url: str
    """The URL of the interview service's update endpoint."""


@frozen
class Config:
    """The main config class."""

    database: DatabaseConfig
    auth: AuthConfig
    payment: PaymentConfig
    interview: InterviewConfig
