"""JSON serialization types."""
import base64
from collections.abc import Callable
from datetime import date, datetime
from functools import cache
from pathlib import PurePath
from typing import Any, Mapping, Union
from uuid import UUID

import orjson

TypeFn = Callable[[Any], bool]
Serializer = Callable[[Any], object]

serializers: Mapping[TypeFn, Serializer] = {
    # Sets to lists
    lambda cls: issubclass(cls, (set, frozenset)): lambda v: sorted(v),
    # UUIDs
    lambda cls: issubclass(cls, UUID): lambda v: str(v),
    # dates
    lambda cls: issubclass(cls, (date, datetime)): lambda v: v.isoformat(),
    # paths
    lambda cls: issubclass(cls, PurePath): lambda v: str(v),
    # bytes
    lambda cls: cls is bytes
    or cls is bytearray: lambda v: base64.b64encode(v).decode(),
}
"""Mapping of JSON serialization handlers."""


def json_dumps(obj: object) -> bytes:
    """JSON dumps function."""
    return orjson.dumps(obj, default=json_default)


def json_loads(v: Union[str, bytes]) -> Any:
    """JSON loads function."""
    return orjson.loads(v)


def json_default(v: object) -> object:
    """JSON default type handler."""
    type_ = type(v)
    serializer = _get_serializer(type_)  # type: ignore
    return serializer(v)


@cache
def _get_serializer(type_: Any) -> Serializer:
    for type_fn, serializer in serializers.items():
        if type_fn(type_):
            return serializer

    raise TypeError(f"Cannot JSON serialize type: {type_}")
