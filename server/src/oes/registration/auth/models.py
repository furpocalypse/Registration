"""Auth models."""
from __future__ import annotations

import base64
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Literal, NewType, Optional, Sequence, Union
from uuid import UUID

import jwt
from attrs import Factory, field, frozen
from cattrs import BaseValidationError
from cattrs.gen import make_dict_unstructure_fn
from cattrs.preconf.json import make_converter
from guardpost import Identity
from jwt import InvalidTokenError
from oes.registration.util import get_now
from typing_extensions import Self

ISSUER = "oes.registration"
AUDIENCE = "oes.registration"
ALGORITHM = "HS256"

DEFAULT_ACCESS_TOKEN_LIFETIME = 900
"""Default access token lifetime, in seconds."""

DEFAULT_REFRESH_TOKEN_LIFETIME = 86400
"""Default refresh token lifetime, in seconds."""

converter = make_converter()


class CredentialType(str, Enum):
    """Credential types."""

    refresh_token = "refresh_token"
    webauthn = "webauthn"


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


Scopes = NewType("Scopes", frozenset[str])

DEFAULT_SCOPES = Scopes(
    frozenset(
        {
            Scope.event,
            Scope.cart,
            Scope.self_service,
        }
    )
)
"""The default scopes users will receive."""


class TokenBase:
    """Base class for JWTs."""

    iss: Optional[str]
    sub: Optional[str]
    aud: Union[str, Sequence[str], None]
    exp: datetime
    nbf: Optional[datetime]
    iat: Optional[datetime]
    jti: Optional[str]

    def encode(self, *, key: str) -> str:
        """Encode the token."""
        as_dict = converter.unstructure(self)
        return jwt.encode(as_dict, key=key, algorithm=ALGORITHM)

    @classmethod
    def decode(
        cls,
        token: str,
        *,
        key: str,
        issuer: Optional[str] = ISSUER,
        audience: Optional[str] = AUDIENCE,
    ) -> Self:
        """Decode/verify/validate a token.

        Raises:
            jwt.InvalidTokenError: If the token is not valid.
        """
        res = jwt.decode(
            token,
            key=key,
            algorithms=[ALGORITHM],
            audience=audience,
            issuer=issuer,
        )
        try:
            return converter.structure(res, cls)
        except BaseValidationError as e:
            raise InvalidTokenError(e)


@frozen
class AccessToken(TokenBase):
    """JWT access token."""

    typ: Literal["at"]
    iss: str
    aud: Union[str, Sequence[str]]
    exp: datetime
    sub: Optional[str] = None
    nbf: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None

    email: Optional[str] = None
    scope: Scopes = field(default=Factory(lambda: Scopes(frozenset())))

    @classmethod
    def create(
        cls,
        account_id: Optional[UUID],
        email: Optional[str],
        scopes: Iterable[str],
    ) -> Self:
        """Create an access token.

        Args:
            account_id: The account ID.
            email: The email.
            scopes: The scopes.
        """
        scope_set = Scopes(frozenset(scopes))
        return cls(
            typ="at",
            iss=ISSUER,
            aud=AUDIENCE,
            exp=get_now() + timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME),
            sub=account_id.hex if account_id is not None else None,
            email=email,
            scope=scope_set,
        )

    def has_scope(self, *scopes: str) -> bool:
        """Return whether the token has all the given scopes."""
        return all(s in self.scope for s in scopes)

    @property
    def is_admin(self) -> bool:
        """Whether the token has the "admin" scope."""
        return self.has_scope(Scope.admin)


@frozen(kw_only=True)
class RefreshToken(TokenBase):
    """Refresh token."""

    typ: Literal["rt"]
    jti: str
    iss: str
    sub: str
    aud: Union[str, Sequence[str]]
    iat: datetime
    exp: datetime
    scope: Scopes = field(default=Factory(lambda: Scopes(frozenset())))
    nbf: Optional[datetime] = None

    @property
    def token_info(self) -> tuple[str, int]:
        """The credential ID and number of this refresh number."""
        token_id_str, _, num_str = self.jti.rpartition(":")
        return token_id_str, int(num_str)

    @classmethod
    def create(
        cls,
        *,
        account_id: UUID,
        credential_id: str,
        token_num: int,
        scopes: Iterable[str],
        expiration_date: Optional[datetime] = None,
    ) -> Self:
        """Create a refresh token.

        Args:
            account_id: The account ID.
            credential_id: The ID of this family of refresh tokens.
            token_num: The token number.
            scopes: The scopes for this token.
            expiration_date: The date this token expires.
        """
        exp = (
            expiration_date
            if expiration_date is not None
            else get_now() + timedelta(seconds=DEFAULT_REFRESH_TOKEN_LIFETIME)
        )

        return cls(
            typ="rt",
            jti=f"{credential_id}:{token_num}",
            iss=ISSUER,
            sub=account_id.hex,
            aud=AUDIENCE,
            iat=get_now(),
            exp=exp,
            scope=Scopes(frozenset(scopes)),
        )


class User(Identity):
    """User implementation."""

    def __init__(self, token: AccessToken):
        claims = converter.unstructure(token)
        super().__init__(claims, "access_token")
        self.token = token

    @property
    def id(self) -> Optional[UUID]:
        return UUID(self["sub"])

    @property
    def email(self) -> Optional[str]:
        return self["email"]

    @property
    def scope(self) -> Scopes:
        return self.token.scope

    def has_scope(self, *scopes: str) -> bool:
        """Return whether the token has all the given scopes."""
        return self.token.has_scope(*scopes)

    @property
    def is_admin(self) -> bool:
        """Whether the token has the "admin" scope."""
        return self.token.is_admin


@frozen
class WebAuthnRegistrationChallenge(TokenBase):
    """Signed WebAuthn registration challenge."""

    typ: Literal["warc"]
    sub: str
    """The challenge data."""

    acc: str
    """The account ID."""

    org: str
    """The origin."""

    exp: datetime

    iss: Optional[str] = None
    aud: Union[str, Sequence[str], None] = None
    nbf: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None

    @classmethod
    def create(cls, account_id: UUID, challenge_bytes: bytes, origin: str) -> Self:
        """Create a :class:`WebAuthnRegistrationChallenge`."""
        return cls(
            typ="warc",
            sub=base64.urlsafe_b64encode(challenge_bytes).decode(),
            acc=account_id.hex,
            org=origin,
            exp=get_now() + timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME),
        )


@frozen
class WebAuthnAuthenticationChallenge(TokenBase):
    """Signed WebAuthn authentication challenge."""

    typ: Literal["waac"]
    sub: str
    """The challenge data."""

    acc: str
    """The account ID."""

    org: str
    """The origin."""

    exp: datetime

    iss: Optional[str] = None
    aud: Union[str, Sequence[str], None] = None
    nbf: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None

    @classmethod
    def create(cls, account_id: UUID, challenge_bytes: bytes, origin: str) -> Self:
        """Create a :class:`WebAuthnRegistrationChallenge`."""
        return cls(
            typ="waac",
            sub=base64.urlsafe_b64encode(challenge_bytes).decode(),
            acc=account_id.hex,
            org=origin,
            # TODO: timeout duration
            exp=get_now() + timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME),
        )


@frozen(kw_only=True)
class TokenResponse:
    """A token response object."""

    access_token: str
    expires_in: int
    refresh_token: str
    scope: str
    token_type: str = "Bearer"


def parse_scope(scope: str) -> Scopes:
    """Split a scope string into a frozenset."""
    return Scopes(frozenset(s for s in scope.split(" ") if s))


def join_scope(scopes: Iterable[str]) -> str:
    """Join scopes into a space delimited string."""
    return " ".join(scopes)


# Datetimes are represented as unix timestamps
converter.register_unstructure_hook(datetime, lambda v: int(v.timestamp()))

converter.register_structure_hook(
    datetime, lambda v, t: datetime.fromtimestamp(v, tz=timezone.utc)
)

# Handle audience
converter.register_structure_hook(
    Union[str, Sequence[str]],
    lambda v, t: v if isinstance(v, str) else converter.structure(v, tuple[str]),
)

# Handle scopes
converter.register_unstructure_hook(Scopes, lambda v: join_scope(v))
converter.register_structure_hook(Scopes, lambda v, t: parse_scope(v))

# Omit default values from tokens
converter.register_unstructure_hook(
    AccessToken,
    make_dict_unstructure_fn(
        AccessToken,
        converter,
        _cattrs_omit_if_default=True,
    ),
)

converter.register_unstructure_hook(
    RefreshToken,
    make_dict_unstructure_fn(
        RefreshToken,
        converter,
        _cattrs_omit_if_default=True,
    ),
)

converter.register_unstructure_hook(
    WebAuthnRegistrationChallenge,
    make_dict_unstructure_fn(
        WebAuthnRegistrationChallenge,
        converter,
        _cattrs_omit_if_default=True,
    ),
)

converter.register_unstructure_hook(
    WebAuthnAuthenticationChallenge,
    make_dict_unstructure_fn(
        WebAuthnAuthenticationChallenge,
        converter,
        _cattrs_omit_if_default=True,
    ),
)
