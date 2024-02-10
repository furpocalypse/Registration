"""User module."""
from abc import abstractmethod
from typing import Optional
from uuid import UUID

from guardpost import Identity
from oes.registration.auth.scope import Scope, Scopes
from typing_extensions import Protocol


class User(Protocol):
    """User information."""

    @property
    @abstractmethod
    def id(self) -> Optional[UUID]:
        """The user/account ID."""
        ...

    @property
    @abstractmethod
    def email(self) -> Optional[str]:
        """The email."""
        ...

    @property
    @abstractmethod
    def scope(self) -> Scopes:
        """The user's allowed scopes."""
        ...

    def has_scope(self, *scopes: str) -> bool:
        """Return whether the token has all the given scopes."""
        return all(s in self.scope for s in scopes)

    @property
    def is_admin(self) -> bool:
        """Whether the token has the "admin" scope."""
        return self.has_scope(Scope.admin)


class UserIdentity(Identity, User):
    """A :class:`User` implementation."""

    def __init__(
        self,
        id: Optional[UUID] = None,
        email: Optional[str] = None,
        scope: Optional[Scopes] = None,
    ):
        super().__init__(
            {
                "id": id,
                "email": email,
                "scope": scope if scope is not None else Scopes(),
            },
            "Bearer",
        )

    @property
    def id(self) -> Optional[UUID]:
        """The user/account ID."""
        return self.claims["id"]

    @property
    def email(self) -> Optional[str]:
        """The email."""
        return self.claims["email"]

    @property
    def scope(self) -> Scopes:
        """The user's allowed scopes."""
        return self.claims["scope"]
