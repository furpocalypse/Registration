"""Common utilities."""
import base64
from collections.abc import Mapping, MutableMapping
from datetime import datetime, timezone
from typing import Optional, TypeVar

from blacksheep.exceptions import NotFound

T = TypeVar("T")


def get_now(seconds_only: bool = False) -> datetime:
    """Get the current tz-aware UTC datetime.

    Args:
        seconds_only: Don't include microseconds.
    """
    dt = datetime.now(tz=timezone.utc)
    if seconds_only:
        dt = dt.replace(microsecond=0)

    return dt


def check_not_found(obj: Optional[T]) -> T:
    """Raise :class:`NotFound` if the argument is null.

    Returns:
        The not-None ``obj``.
    """
    if obj is None:
        raise NotFound
    return obj


def merge_dict(a: MutableMapping, b: Mapping):
    """Merge ``a`` and ``b`` in place, mutating ``a``."""
    for k, v in b.items():
        cur_a_val = a.get(k)
        if (
            cur_a_val is not None
            and isinstance(v, dict)
            and isinstance(cur_a_val, dict)
        ):
            merge_dict(cur_a_val, v)
        else:
            a[k] = v


def unpadded_urlsafe_b64decode(b: str) -> bytes:
    """URL-safe base64 decode that accepts missing padding."""
    return base64.urlsafe_b64decode(b + "==")
