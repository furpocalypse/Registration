"""Scope module."""
from collections.abc import Set
from enum import Enum
from typing import Iterable, Iterator

from attrs import frozen


class Scope(str, Enum):
    """Authorization scopes."""

    admin = "admin"
    """May use administration endpoints."""

    cart = "cart"
    """May use cart and checkout endpoints."""

    event = "event"
    """May use event endpoints."""

    self_service = "self-service"
    """May use self-service endpoints and manage one's own registrations."""


@frozen(init=False, repr=False, order=False)
class Scopes(Set[str]):
    """A set of scopes."""

    _set: frozenset[str]

    def __init__(self, iterable: Iterable[str] = ()):
        if isinstance(iterable, Scopes):
            values = iterable._set
        elif isinstance(iterable, str):
            values = frozenset(iterable.split())
        else:
            values = frozenset(iterable)

        object.__setattr__(self, "_set", values)

    def __contains__(self, x: object) -> bool:
        return x in self._set

    def __len__(self) -> int:
        return len(self._set)

    def __iter__(self) -> Iterator[str]:
        return iter(self._set)

    def __str__(self) -> str:
        return " ".join(sorted(self))

    def __repr__(self) -> str:
        strs = ", ".join(repr(s) for s in sorted(self))
        return f"{{{strs}}}"


DEFAULT_SCOPES = Scopes((Scope.event, Scope.cart, Scope.self_service))
"""The default scopes."""
