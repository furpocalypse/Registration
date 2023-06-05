"""Auth handlers."""
from collections.abc import Callable
from typing import Any, Optional

from blacksheep import Request
from blacksheep.server.bindings import Binder, BoundValue
from guardpost import Identity
from guardpost.asynchronous.authentication import AuthenticationHandler
from jwt import InvalidTokenError
from oes.registration.models.auth import AccessToken, User
from oes.registration.models.config import Config


class TokenAuthHandler(AuthenticationHandler):
    """Handler to allow the web server to use token auth."""

    def __init__(self, config: Config):
        self.config = config

    def decode_token(self, value: bytes) -> Optional[AccessToken]:
        try:
            token = AccessToken.decode(value.decode(), key=self.config.auth.signing_key)
        except InvalidTokenError:
            return None

        return token

    async def authenticate(self, context: Request) -> Optional[Identity]:
        auth_header = context.headers.get_first(b"Authorization")
        if not auth_header:
            return None

        typ, _, value = auth_header.partition(b" ")
        if typ.lower() != b"bearer":
            return None

        token = self.decode_token(value)
        if token:
            user = User(token)
            context.identity = user
            return user
        else:
            context.identity = None
            return None


class RequestUser(BoundValue[User]):
    """Bound value for the app specific :class:`User` class."""

    pass


class UserBinder(Binder):
    """User binder.

    Even though not explicitly used, this is required to support implicitly binding a
    :class: `Identity` subclass.
    """

    handle = RequestUser
    type_alias = User

    def __init__(
        self,
        expected_type: Any = User,
        name: str = "",
        implicit: bool = True,
        required: bool = True,
        converter: Optional[Callable] = None,
    ):
        super().__init__(expected_type, name, implicit, required, converter)

    async def get_value(self, request: Request) -> Optional[User]:
        return getattr(request, "identity", None)
