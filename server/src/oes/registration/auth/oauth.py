"""OAuth module."""
from collections.abc import Set, Iterable, Iterator
from enum import Enum

from attrs import frozen
from oauthlib.oauth2 import RequestValidator

JS_CLIENT_ID = "oes"
"""The client ID of the JS frontend."""


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


class Scopes(Set[str]):
    """A collection of scopes."""

    def __init__(self, iterable: Iterable[str] = ()):
        if isinstance(iterable, str):
            self._set = frozenset(iterable.split())
        else:
            self._set = frozenset(iterable)

    def __contains__(self, x: object) -> bool:
        return x in self._set

    def __len__(self) -> int:
        return len(self._set)

    def __iter__(self) -> Iterator[str]:
        return iter(self._set)

    def __str__(self) -> str:
        return " ".join(str(s) for s in sorted(self._set))

    def __repr__(self) -> str:
        values = ", ".join(repr(str(s)) for s in sorted(self._set))
        return f"{{{values}}}"

    def __eq__(self, other) -> bool:
        return self._set == other

    def __hash__(self) -> int:
        return hash(self._set)

@frozen
class Client:
    id: str
    """The client ID."""


class Validator(RequestValidator):
    def validate_client_id(self, client_id, request, *args, **kwargs):
        """Validate the client ID."""
        if client_id == JS_CLIENT_ID:
            # TODO: set client obj
            request.client = object()
            return True
        return False

