"""Serialization package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oes.registration.serialization.common import CustomConverter


def get_config_converter() -> CustomConverter:
    """Get a :class:`Converter`."""
    from oes.registration.serialization.config import converter

    return converter


def get_converter() -> CustomConverter:
    """Get a :class:`Converter` suitable for validating external data."""
    from oes.registration.serialization.data import converter

    return converter
