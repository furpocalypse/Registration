"""Auth handlers."""
from collections.abc import Callable
from typing import Any, Optional
from uuid import UUID

from attrs import evolve
from blacksheep import Request
from blacksheep.exceptions import Forbidden
from blacksheep.server.bindings import Binder, BoundValue
from guardpost import Identity, Policy
from guardpost.asynchronous.authentication import AuthenticationHandler
from guardpost.authorization import AuthorizationContext
from guardpost.synchronous.authorization import Requirement
from jwt import InvalidTokenError
from oes.registration.auth.scope import Scope, Scopes
from oes.registration.auth.token import AccessToken
from oes.registration.auth.user import User, UserIdentity
from oes.registration.config import CommandLineConfig
from oes.registration.models.config import Config


class TokenAuthHandler(AuthenticationHandler):
    """Handler to allow the web server to use token auth."""

    def __init__(self, cmd_config: CommandLineConfig, config: Config):
        self.cmd_config = cmd_config
        self.config = config

    async def authenticate(self, context: Request) -> Optional[Identity]:
        token_val = _get_token(context)
        token = (
            _decode_token(token_val, key=self.config.auth.signing_key)
            if token_val
            else None
        )

        if token:
            token = self._apply_debug_settings(token)

            user = UserIdentity(
                id=UUID(token.sub) if token.sub else None,
                email=token.email,
                scope=token.scope,
            )
            context.identity = user
            return user
        else:
            context.identity = None
            return None

    def _apply_debug_settings(self, token: AccessToken) -> AccessToken:
        # If the testing no_auth setting is enabled, override scopes
        if self.cmd_config.insecure and self.cmd_config.no_auth:
            token = evolve(
                token,
                scope=Scopes(Scope.__members__.values()),
            )
        return token


def _get_token(request: Request) -> Optional[str]:
    header = request.get_first_header(b"Authorization")
    if not header:
        return None

    typ, _, value = header.partition(b" ")
    if typ.lower() != b"bearer":
        return None

    return header.decode()


def _decode_token(value: str, *, key: str) -> Optional[AccessToken]:
    try:
        token = AccessToken.decode(value, key=key)
    except InvalidTokenError:
        return None

    return token


class ScopeRequirement(Requirement):
    """Require a scope."""

    def __init__(self, scope: Scope):
        self.scope = scope

    def handle(self, context: AuthorizationContext):
        identity = context.identity

        if not identity:
            context.fail("Missing identity")
            return

        if not isinstance(identity, UserIdentity) or self.scope not in identity.scope:
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
    """Bound value for the app specific :class:`User` interface."""

    pass


class UserBinder(Binder):
    """User binder.

    Even though not explicitly used, this is required to support implicitly binding
    :class:`User`.
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
