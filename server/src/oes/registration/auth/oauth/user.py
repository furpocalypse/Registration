"""User module."""
from typing import Optional
from uuid import UUID

from guardpost import Identity
from oes.registration.auth.oauth.scope import Scope, Scopes


class User(Identity):
    """A user."""

    @property
    def id(self) -> Optional[UUID]:
        """The user's ID."""
        return self["id"]

    @property
    def email(self) -> Optional[str]:
        """The user's email."""
        return self["email"]

    @property
    def scope(self) -> Scopes:
        """The user's scopes."""
        scopes = self["scope"]
        return scopes if scopes is not None else Scopes()

    def has_scope(self, *scopes: str) -> bool:
        """Return whether the token has all the given scopes."""
        return all(s in self.scope for s in scopes)

    @property
    def is_admin(self) -> bool:
        """Whether the token has the "admin" scope."""
        return self.has_scope(Scope.admin)
