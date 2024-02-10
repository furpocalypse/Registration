"""Common utilities."""
import base64
from collections.abc import Mapping, MutableMapping
from datetime import datetime, timezone
from typing import Optional, TypeVar, Union

from blacksheep import URL, Request
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


def unpadded_urlsafe_b64encode(b: Union[str, bytes]) -> str:
    """URL-safe base64 encode that removes the padding."""
    enc = base64.urlsafe_b64encode(b.encode() if isinstance(b, str) else b)
    return enc.decode().rstrip("=")


def unpadded_urlsafe_b64decode(b: Union[str, bytes]) -> bytes:
    """URL-safe base64 decode that accepts missing padding."""
    if isinstance(b, bytes):
        return base64.urlsafe_b64decode(b + b"==")
    else:
        return base64.urlsafe_b64decode(b + "==")


def get_origin(request: Request) -> str:
    """Get the request origin."""
    origin = request.get_first_header(b"Origin")
    if origin:
        return normalize_origin(origin.decode())
    else:
        host = request.host
        scheme = request.scheme
        return normalize_origin(f"{scheme}://{host}")


def normalize_origin(origin: str) -> str:
    """Remove the default port from an origin string."""
    url = URL(origin.encode())
    assert url.schema is not None
    assert url.host is not None

    result = (url.schema + b"://" + url.host).decode()

    if (
        url.schema == b"https"
        and url.port == 443
        or url.schema == b"http"
        and url.port == 80
    ):
        return result
    else:
        return f"{result}:{url.port}"


def origin_to_rp_id(origin: str) -> str:
    """Get the relying party ID from an origin string."""
    url = URL(origin.encode())
    assert url.host is not None
    return url.host.decode()
