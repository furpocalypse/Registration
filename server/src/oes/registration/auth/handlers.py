"""Auth handlers."""
from collections.abc import Callable
from typing import Any, Optional

from attrs import evolve
from blacksheep import Request
from blacksheep.exceptions import Forbidden
from blacksheep.server.bindings import Binder, BoundValue
from guardpost import Identity, Policy
from guardpost.asynchronous.authentication import AuthenticationHandler
from guardpost.authorization import AuthorizationContext
from guardpost.synchronous.authorization import Requirement
from jwt import InvalidTokenError
from oes.registration.auth.models import AccessToken, Scope, Scopes, User
from oes.registration.config import CommandLineConfig
from oes.registration.models.config import Config


class TokenAuthHandler(AuthenticationHandler):
    """Handler to allow the web server to use token auth."""

    def __init__(self, cmd_config: CommandLineConfig, config: Config):
        self.cmd_config = cmd_config
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
            # If the testing no_auth setting is enabled, override scopes
            if self.cmd_config.insecure and self.cmd_config.no_auth:
                token = evolve(token, scope=Scopes(frozenset(s for s in Scope)))

            user = User(token)
            context.identity = user
            return user
        else:
            context.identity = None
            return None


class ScopeRequirement(Requirement):
    """Require a scope."""

    def __init__(self, scope: Scope):
        self.scope = scope

    def handle(self, context: AuthorizationContext):
        identity = context.identity

        if not identity:
            context.fail("Missing identity")
            return

        if not isinstance(identity, User) or not identity.has_scope(self.scope):
            context.fail(f"Missing scope {self.scope}")
            # workaround: the authorization framework returns 401 instead of 403...
            raise Forbidden

        context.succeed(self)


RequireEvent = "require_event"
RequireCart = "require_cart"
RequireSelfService = "require_self_service"
RequireAdmin = "require_admin"

require_event = Policy(RequireEvent, ScopeRequirement(Scope.event))
require_admin = Policy(RequireAdmin, ScopeRequirement(Scope.admin))
require_self_service = Policy(RequireSelfService, ScopeRequirement(Scope.self_service))
require_cart = Policy(RequireCart, ScopeRequirement(Scope.cart))


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
