"""Common converters."""
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Type, TypeVar, Union
from uuid import UUID

from cattrs import Converter
from oes.registration.serialization.json import json_dumps, json_loads

T = TypeVar("T")


class CustomConverter(Converter):
    """Converter that uses orjson."""

    def dumps(self, obj: object, unstructure_as=None) -> bytes:
        unstructured = self.unstructure(obj, unstructure_as)
        return json_dumps(unstructured)

    def loads(self, value: Union[str, bytes], cl: Type[T]) -> T:
        obj = json_loads(value)
        return self.structure(obj, cl)


def structure_datetime(v: object) -> datetime:
    if isinstance(v, datetime):
        dt = v
    elif isinstance(v, (float, int)):
        dt = datetime.fromtimestamp(v, tz=timezone.utc)
    elif isinstance(v, str):
        dt = datetime.fromisoformat(v)
    else:
        raise TypeError(f"Invalid datetime: {v!r}")

    if dt.tzinfo is None:
        dt = dt.astimezone()

    return dt


def structure_date(v: object) -> date:
    if isinstance(v, date):
        return v
    elif isinstance(v, str):
        return date.fromisoformat(v)
    else:
        raise TypeError(f"Invalid date: {v!r}")


def structure_uuid(v: object) -> UUID:
    if isinstance(v, UUID):
        return v
    elif isinstance(v, str):
        return UUID(v)
    else:
        raise TypeError(f"Invalid UUID: {v!r}")


def structure_path(v: object) -> Path:
    if isinstance(v, Path):
        return v
    elif isinstance(v, str):
        return Path(v)
    else:
        raise TypeError(f"Invalid path: {v!r}")


converter = CustomConverter()

structure_funcs = {
    lambda cls: issubclass(cls, UUID): lambda v, t: structure_uuid(v),
    lambda cls: cls is datetime: lambda v, t: structure_datetime(v),
    lambda cls: cls is date: lambda v, t: structure_date(v),
    lambda cls: issubclass(cls, Path): lambda v, t: structure_path(v),
}


def configure_converter(c: Converter):
    for test_func, func in structure_funcs.items():
        c.register_structure_hook_func(test_func, func)


configure_converter(converter)
