"""Token module."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal, Optional, Sequence, Union
from uuid import UUID

import jwt
from attrs import fields, frozen
from cattrs import BaseValidationError, override
from cattrs.gen import make_dict_unstructure_fn
from cattrs.preconf.orjson import make_converter
from jwt import InvalidTokenError
from oes.registration.auth.scope import Scopes
from oes.registration.util import get_now
from typing_extensions import Self

ALGORITHM = "HS256"

DEFAULT_ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
"""Default access token lifetime."""

DEFAULT_REFRESH_TOKEN_LIFETIME = timedelta(days=90)
"""Default refresh token lifetime."""

WEBAUTHN_REFRESH_TOKEN_LIFETIME = timedelta(hours=1)
"""Default refresh token lifetime for WebAuthn."""

converter = make_converter()
"""A converter for tokens."""


@frozen(kw_only=True)
class TokenBase:
    """Base class for JWTs."""

    iss: Optional[str] = None
    sub: Optional[str] = None
    aud: Union[str, Sequence[str], None] = None
    exp: datetime
    nbf: Optional[datetime] = None
    iat: Optional[datetime] = None
    jti: Optional[str] = None

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
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
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


@frozen(kw_only=True)
class AccessToken(TokenBase):
    """JWT access token."""

    typ: Literal["at"]
    azp: Optional[str] = None

    email: Optional[str] = None
    scope: Scopes = Scopes()

    @classmethod
    def create(
        cls,
        account_id: Union[UUID, str, None],
        scope: Optional[Scopes] = None,
        email: Optional[str] = None,
        client_id: Optional[str] = None,
        expiration_date: Optional[datetime] = None,
    ) -> AccessToken:
        """Create an access token.

        Args:
            account_id: The account ID.
            scope: The token scope.
            email: The email.
            client_id: The client ID.
            expiration_date: A non-default expiration date.
        """
        exp = (
            expiration_date
            if expiration_date is not None
            else (get_now(seconds_only=True) + DEFAULT_ACCESS_TOKEN_LIFETIME)
        )

        return cls(
            typ="at",
            exp=exp,
            sub=account_id.hex if isinstance(account_id, UUID) else account_id,
            email=email,
            azp=client_id,
            scope=scope if scope is not None else Scopes(),
        )


@frozen(kw_only=True)
class RefreshToken(TokenBase):
    """JWT refresh token."""

    typ: Literal["rt"]
    jti: str
    azp: Optional[str] = None

    email: Optional[str] = None
    scope: Scopes = Scopes()

    @property
    def credential_id(self) -> str:
        """The ID of this series of refresh tokens."""
        id_, _, _ = self.jti.rpartition(":")
        return id_

    @property
    def token_num(self) -> int:
        """The number of this refresh token."""
        _, _, num_str = self.jti.rpartition(":")
        return int(num_str)

    @classmethod
    def create(
        cls,
        account_id: Union[UUID, str, None],
        credential_id: str,
        token_num: int,
        scope: Optional[Scopes] = None,
        email: Optional[str] = None,
        client_id: Optional[str] = None,
        issue_date: Optional[datetime] = None,
        expiration_date: Optional[datetime] = None,
    ) -> RefreshToken:
        """Create a :class:`RefreshToken`.

        Args:
            account_id: The account ID.
            credential_id: The ID of this series of refresh tokens.
            token_num: The number of this refresh token.
            scope: The scope of the token.
            email: The email.
            client_id: The client ID.
            issue_date: The issue date of this token.
            expiration_date: A non-default expiration date.
        """
        iat = issue_date if issue_date is not None else get_now(seconds_only=True)
        exp = (
            expiration_date
            if expiration_date is not None
            else (iat + DEFAULT_REFRESH_TOKEN_LIFETIME)
        )

        token_id = f"{credential_id}:{token_num}"

        return cls(
            typ="rt",
            sub=account_id.hex if isinstance(account_id, UUID) else account_id,
            exp=exp,
            jti=token_id,
            scope=scope if scope is not None else Scopes(),
            email=email,
            azp=client_id,
        )

    def reissue_refresh_token(self) -> RefreshToken:
        """Create a :class:`RefreshToken` with an incremented ``token_num``."""
        diff = (
            (self.exp - self.iat)
            if self.iat is not None
            else DEFAULT_REFRESH_TOKEN_LIFETIME
        )
        now = get_now(seconds_only=True)
        exp = now + diff

        return self.create(
            account_id=self.sub,
            credential_id=self.credential_id,
            token_num=self.token_num + 1,
            scope=self.scope,
            email=self.email,
            client_id=self.azp,
            issue_date=now,
            expiration_date=exp,
        )

    def create_access_token(
        self,
        *,
        scope: Optional[Scopes] = None,
        expiration_date: Optional[datetime] = None,
    ) -> AccessToken:
        """Create an access token from this refresh token.

        Args:
            scope: Optional reduced scope for the resulting token.
            expiration_date: A non-default expiration date.
        """
        return AccessToken.create(
            account_id=self.sub,
            scope=Scopes((self.scope & scope) if scope is not None else self.scope),
            email=self.email,
            expiration_date=expiration_date,
            client_id=self.azp,
        )


@frozen(kw_only=True)
class TokenResponse:
    """An OAuth token response."""

    token_type: str = "Bearer"
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None

    @classmethod
    def create(
        cls,
        *,
        access_token: Optional[AccessToken] = None,
        refresh_token: Optional[RefreshToken] = None,
        scope: Union[str, Scopes, None] = None,
        expires_in: Optional[int] = None,
        key: str,
    ) -> Self:
        """Create a :class:`TokenResponse`.

        Args:
            access_token: The access token.
            refresh_token: The refresh token.
            scope: The scope.
            expires_in: The ``expires_in`` value.
            key: The signing key.
        """
        enc_access_token = (
            access_token.encode(key=key) if access_token is not None else None
        )
        enc_refresh_token = (
            refresh_token.encode(key=key) if refresh_token is not None else None
        )

        return cls(
            token_type="Bearer",
            access_token=enc_access_token,
            refresh_token=enc_refresh_token,
            scope=_scope_to_str(scope),
            expires_in=_compute_expires_in(expires_in, access_token),
        )


def _compute_expires_in(
    expires_in: Optional[int],
    access_token: Optional[AccessToken],
) -> Optional[int]:
    if expires_in is not None:
        return expires_in

    if access_token is None:
        return None
    now = (
        access_token.iat if access_token.iat is not None else get_now(seconds_only=True)
    )
    return int((access_token.exp - now).total_seconds())


def _scope_to_str(scope: Union[str, Scopes, None]) -> Optional[str]:
    if isinstance(scope, str):
        return scope
    elif isinstance(scope, Scopes):
        return str(scope)
    else:
        return None


# Structure/unstructure hooks
def _structure_datetime(v, t):
    if isinstance(v, int):
        return datetime.fromtimestamp(v).astimezone()
    else:
        raise TypeError(f"Invalid date: {v}")


converter.register_structure_hook(datetime, _structure_datetime)
converter.register_unstructure_hook(datetime, lambda v: int(v.timestamp()))


def _structure_scope(v, t):
    if isinstance(v, str):
        return Scopes(v)
    else:
        raise TypeError(f"Invalid scope: {v}")


converter.register_structure_hook(Scopes, _structure_scope)
converter.register_unstructure_hook(Scopes, lambda v: str(v))


def _make_unstructure_excluding_none(c, cls):
    overrides = {
        f.name: override(omit_if_default=True) for f in fields(cls) if f.default is None
    }
    return make_dict_unstructure_fn(cls, c, **overrides)


converter.register_unstructure_hook_factory(
    lambda cls: issubclass(cls, TokenBase),
    lambda cls: _make_unstructure_excluding_none(converter, cls),
)
