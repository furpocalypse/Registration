"""Converter for working with user input."""
from builtins import issubclass
from collections.abc import Sequence
from enum import Enum
from typing import Tuple, Union, get_args, get_origin

from attr import resolve_types
from attrs import fields
from cattrs import Converter
from cattrs.gen import make_dict_unstructure_fn
from oes.registration.models.registration import (
    Registration,
    WritableRegistration,
    structure_registration,
    structure_writable_registration,
    unstructure_registration,
)
from oes.registration.serialization.common import CustomConverter
from oes.registration.serialization.common import (
    configure_converter as configure_common,
)
from oes.registration.views.responses import ExceptionDetails

converter = CustomConverter()
configure_common(converter)


# Sequence[T] is structured as tuple[T, ...]
def structure_sequence(c, v, t):
    args = get_args(t)
    return c.structure(v, Tuple[args[0], ...])


def structure_without_cast(v, t):
    """Structure a type without attempting to cast the value."""
    if isinstance(v, t):
        return v
    elif (
        issubclass(t, (int, float))
        and isinstance(v, (int, float))
        or issubclass(t, Enum)
        and isinstance(v, (int, str))
    ):
        return t(v)
    else:
        raise TypeError(f"Invalid type: {v!r}")


def _is_nullable(t):
    origin = get_origin(t)
    args = get_args(t)
    return origin is Union and type(None) in args


def make_unstructure_dict_omitting_none(c, t):
    """Make an unstructure function that omits None."""

    # Resolve types because some field types might just be strings
    resolve_types(t)

    nullable_fields = [f.name for f in fields(t) if _is_nullable(f.type)]

    unstructure_fn = make_dict_unstructure_fn(t, c)

    def unstructure(v):
        dict_ = unstructure_fn(v)
        for field in nullable_fields:
            if field in dict_ and dict_[field] is None:
                del dict_[field]
        return dict_

    return unstructure


def configure_converter(c: Converter):
    for t in (float, int, bool, str):
        c.register_structure_hook(t, structure_without_cast)

    c.register_structure_hook_factory(
        lambda cls: get_origin(cls) is Sequence,
        lambda cls: lambda v, t: structure_sequence(c, v, t),
    )

    # Structuring registrations
    c.register_structure_hook(
        Registration,
        lambda v, t: structure_registration(c, v),
    )
    c.register_structure_hook(
        WritableRegistration,
        lambda v, t: structure_writable_registration(c, v),
    )

    # unstructure attrs classes omitting None
    c.register_unstructure_hook_factory(
        lambda cls: hasattr(cls, "__attrs_attrs__"),
        lambda cls: make_unstructure_dict_omitting_none(c, cls),
    )

    # Unstructuring registrations
    c.register_unstructure_hook_func(
        lambda cls: cls is Registration
        or cls is WritableRegistration
        or cls == Union[Registration, WritableRegistration],
        lambda v: unstructure_registration(c, v),
    )

    # Exception details
    c.register_unstructure_hook_factory(
        lambda cls: issubclass(cls, ExceptionDetails),
        lambda cls: make_dict_unstructure_fn(
            ExceptionDetails,
            c,
            _cattrs_omit_if_default=True,
        ),
    )


configure_converter(converter)
