"""Serialization used internally for configuration."""
import base64
from collections.abc import Sequence
from typing import Tuple, get_args, get_origin

from cattrs import Converter
from oes.registration.models.config import Base64Bytes
from oes.registration.serialization.common import CustomConverter
from oes.registration.serialization.common import (
    configure_converter as configure_common,
)
from oes.template import (
    Condition,
    Expression,
    LogicAnd,
    LogicOr,
    Template,
    structure_condition,
    structure_expression,
    structure_template,
    unstructure_and,
    unstructure_expression,
    unstructure_or,
    unstructure_template,
)

converter = CustomConverter()
configure_common(converter)


# Sequence[T] is structured as tuple[T, ...]
def structure_sequence(c, v, t):
    args = get_args(t)
    return c.structure(v, Tuple[args[0], ...])


def structure_base64_bytes(v, t):
    if isinstance(v, (bytes, bytearray)):
        return bytes(v)
    elif not isinstance(v, str):
        raise TypeError(f"Invalid base64 data: {v!r}")

    decoded = base64.b64decode(v)
    return Base64Bytes(decoded)


def unstructure_base64_bytes(v):
    if isinstance(v, str):
        return v
    elif not isinstance(v, (bytes, bytearray)):
        raise TypeError(f"Invalid bytes: {v!r}")

    encoded = base64.b64encode(v)
    return encoded.decode()


def configure_converter(c: Converter):
    c.register_structure_hook(Base64Bytes, structure_base64_bytes)
    c.register_structure_hook_func(
        lambda cls: get_origin(cls) is Sequence,
        lambda v, t: structure_sequence(c, v, t),
    )
    c.register_structure_hook(Template, lambda v, t: structure_template(v))
    c.register_structure_hook(
        Expression,
        lambda v, t: structure_expression(v),
    )
    c.register_structure_hook(
        Condition,
        lambda v, t: structure_condition(c, v),
    )

    c.register_unstructure_hook(Base64Bytes, unstructure_base64_bytes)
    c.register_unstructure_hook(Template, unstructure_template)
    c.register_unstructure_hook(Expression, unstructure_expression)
    c.register_unstructure_hook(LogicAnd, lambda v: unstructure_and(c, v))
    c.register_unstructure_hook(LogicOr, lambda v: unstructure_or(c, v))


configure_converter(converter)
