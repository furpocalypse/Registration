"""Auth service."""
import copy
import secrets
from collections.abc import Iterable
from datetime import datetime
from typing import Optional, TypeVar
from uuid import UUID

import jwt
import pydantic
import webauthn
from blacksheep import URL, Request
from blacksheep.exceptions import Unauthorized
from jwt import InvalidTokenError
from loguru import logger
from oes.registration.auth.entities import AccountEntity, CredentialEntity
from oes.registration.auth.models import (
    DEFAULT_SCOPES,
    AccessToken,
    CredentialType,
    RefreshToken,
    TokenResponse,
    WebAuthnAuthenticationChallenge,
    WebAuthnRegistrationChallenge,
)
from oes.registration.auth.models import converter as token_converter
from oes.registration.auth.models import join_scope
from oes.registration.models.config import Config
from oes.registration.util import get_now, unpadded_urlsafe_b64decode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from webauthn import generate_authentication_options, verify_authentication_response
from webauthn.helpers.exceptions import (
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticationCredential,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    RegistrationCredential,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)
from webauthn.registration.verify_registration_response import VerifiedRegistration


class AuthorizationError(ValueError):
    """Exception raised when authorization fails."""

    # TODO: this is very vague


def get_access_token_from_request(request: Request) -> Optional[AccessToken]:
    """Get the :class:`AccessToken` from the request."""
    header = request.get_first_header(b"Authorization")
    if header is None:
        return None

    type_, _, value = header.lower().partition(b" ")

    if type_ != b"bearer" or not value:
        raise Unauthorized

    try:
        access_token = AccessToken.decode(value.decode(), key="TODO FIXME")
    except InvalidTokenError as e:
        logger.debug(f"Invalid access token: {e}")
        raise Unauthorized

    return access_token


T = TypeVar("T", bound=Optional[AccessToken])


class AuthService:
    """Auth service."""

    def __init__(
        self,
        db: AsyncSession,
        config: Config,
    ):
        self.db = db
        self.config = config

    async def get_account(
        self, id: UUID, *, lock: bool = False, with_credentials: bool = False
    ) -> Optional[AccountEntity]:
        """Get a :class:`AccountEntity` by ID.

        Args:
            id: The account ID.
            lock: Whether to lock the row.
            with_credentials: Whether to eagerly fetch credentials.
        """
        opts = []

        if with_credentials:
            opts.append(
                joinedload(
                    AccountEntity.credentials,
                    innerjoin=True,
                ).contains_eager(CredentialEntity.account)
            )

        res = await self.db.get(
            AccountEntity,
            id,
            options=opts,
            with_for_update=lock,
            populate_existing=True,
        )
        return res

    async def get_credential(self, id: str) -> Optional[CredentialEntity]:
        """Get a :class:`CredentialEntity` by ID."""
        return await self.db.get(CredentialEntity, id)

    async def create_account(self, email: Optional[str]) -> AccountEntity:
        """Create a new :class:`AccountEntity`.

        Args:
            email: The email address associated with the account.
        """
        account = AccountEntity(email=email, credentials=[])
        self.db.add(account)
        await self.db.flush()
        return account

    async def create_refresh_token(
        self,
        account: AccountEntity,
        token: RefreshToken,
    ) -> CredentialEntity:
        """Create a new :class:`CredentialEntity` for a refresh token.

        Adds the credential to the :class:`AccountEntity`.

        Args:
            account: The account.
            token: The :class:`RefreshToken`.
        """
        credential_id, token_num = token.token_info

        as_dict = token_converter.unstructure(token)

        entity = CredentialEntity(
            id=credential_id,
            type=CredentialType.refresh_token,
            date_created=token.iat,
            date_expires=token.exp,
            data=as_dict,
        )
        account.credentials.append(entity)
        await self.db.flush()
        return entity

    async def create_webauthn_registration(
        self,
        account: AccountEntity,
        registration: VerifiedRegistration,
        challenge: str,
    ) -> CredentialEntity:
        """Create a WebAuthn registration credential.

        Adds the created credential to ``account``.

        Args:
            account: The :class:`AccountEntity`.
            registration: The :class:`VerifiedRegistration`.
            challenge: The challenge that was sent.

        Returns:
            The created credential.

        Raises:
            AuthorizationError: If this credential ID already exists.
        """
        credential_id = registration.credential_id.hex()

        # check that the credential_id is not already registered
        existing = await self.db.get(CredentialEntity, credential_id)
        if existing is not None:
            raise AuthorizationError

        # check that the challenge is not re-used
        _check_challenge_reuse(account, challenge)

        entity = CredentialEntity(
            id=registration.credential_id.hex(),
            type=CredentialType.webauthn,
            date_created=get_now(),
            data={
                "challenge": challenge,
                "registration": registration.dict(by_alias=True),
            },
        )

        account.credentials.append(entity)
        await self.db.flush()
        return entity


async def get_refresh_token_by_str(
    service: AuthService,
    config: Config,
    token_str: str,
    *,
    lock: bool = False,
) -> Optional[tuple[RefreshToken, RefreshToken, CredentialEntity]]:
    """Get a :class:`CredentialEntity` from a signed refresh token string.

    Warning:
        Validates the token, but does not check the current token number.

    Args:
        service: The :class:`AuthService`.
        config: The server config.
        token_str: The token string.
        lock: Whether to lock the account row.

    Returns:
        A tuple of the decoded :class:`RefreshToken`, the current
        :class:`RefreshToken` in the database, and the :class:`CredentialEntity` if
        found/valid, else None.
    """
    try:
        provided_token = RefreshToken.decode(token_str, key=config.auth.signing_key)
    except InvalidTokenError:
        return None

    credential_id, _ = provided_token.token_info
    account_id = UUID(provided_token.sub)
    account = await service.get_account(account_id, lock=lock, with_credentials=True)
    if not account:
        return None

    for cred in account.credentials:
        if cred.id == credential_id:
            current_token = token_converter.structure(cred.data, RefreshToken)
            return provided_token, current_token, cred

    return None


async def create_new_account(
    service: AuthService,
    config: Config,
) -> TokenResponse:
    """Create a new account and issue tokens.

    Args:
        service: The :class:`AuthService`.
        config: The server config.

    Returns:
        A :class:`TokenResponse`.
    """
    now = get_now()
    account = await service.create_account(None)

    access_token = AccessToken.create(
        account_id=account.id,
        email=account.email,
        scopes=DEFAULT_SCOPES,
    )
    signed_access_token = access_token.encode(key=config.auth.signing_key)

    signed_refresh_token, _ = await create_new_refresh_token(
        service,
        config,
        account,
        scopes=DEFAULT_SCOPES,
    )

    token_response = TokenResponse(
        access_token=signed_access_token,
        refresh_token=signed_refresh_token,
        scope=join_scope(access_token.scope),
        expires_in=int((access_token.exp - now).total_seconds()),
    )

    return token_response


def update_refresh_token(
    config: Config,
    credential: CredentialEntity,
    expiration_date: Optional[datetime] = None,
) -> tuple[str, RefreshToken]:
    """Update/re-issue a refresh token.

    Mutates ``credential``.

    Args:
        config: The server configuration.
        credential: The current refresh token.
        expiration_date: A new non-default expiration date.

    Returns:
        A pair of the signed token string, and the new :class:`RefreshToken`.
    """
    token = token_converter.structure(credential.data, RefreshToken)
    _, token_num = token.token_info

    updated = RefreshToken.create(
        account_id=credential.account_id,
        credential_id=credential.id,
        token_num=token_num + 1,
        scopes=token.scope,
        expiration_date=expiration_date,
    )
    signed = updated.encode(key=config.auth.signing_key)

    token_dict = token_converter.unstructure(updated)

    credential.date_updated = updated.iat
    credential.date_last_used = updated.iat
    credential.date_expires = updated.exp
    credential.data = token_dict
    return signed, updated


def get_webauthn_registration_challenge(
    config: Config,
    account_id: UUID,
    origin: str,
    user_name: str,
) -> tuple[str, dict]:
    """Get registration challenge for WebAuthn.

    Returns:
        The signed :class:`WebAuthnRegistrationChallenge` as a string, and the options
        as a dict.
    """
    if origin not in config.auth.allowed_auth_origins:
        logger.debug(f"Origin not allowed: {origin}")
        raise AuthorizationError

    challenge_bytes = secrets.token_bytes(16)

    challenge = WebAuthnRegistrationChallenge.create(
        account_id, challenge_bytes, origin
    )
    signed_challenge = challenge.encode(key=config.auth.signing_key)

    registration_opts = webauthn.generate_registration_options(
        rp_id=_origin_to_rp_id(origin),
        rp_name=config.auth.name,
        user_id=str(account_id),
        user_name=user_name,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.DISCOURAGED,
        ),
        challenge=challenge_bytes,
    )
    return signed_challenge, registration_opts.dict(
        by_alias=True, exclude_unset=False, exclude_none=True
    )


def verify_webauthn_registration_response(
    config: Config, challenge_data: str, response_data: str, origin: str
) -> tuple[UUID, VerifiedRegistration]:
    """Verify the returned registration response.

    Returns:
        A pair of the account ID, and the verified registration.

    Raises:
        AuthorizationError: If the response is invalid.
    """
    if origin not in config.auth.allowed_auth_origins:
        logger.debug(f"Origin not allowed: {origin}")
        raise AuthorizationError

    try:
        challenge = WebAuthnRegistrationChallenge.decode(
            challenge_data,
            key=config.auth.signing_key,
            issuer=None,  # these are not included
            audience=None,
        )
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid webauthn challenge: {e}")
        raise AuthorizationError

    if origin != challenge.org:
        logger.debug(f"Origin mismatch: {origin} != {challenge.org}")
        raise AuthorizationError

    account_id = UUID(challenge.acc)

    try:
        credential = RegistrationCredential.parse_raw(response_data)
    except pydantic.ValidationError:
        logger.debug("Invalid webauthn credential")
        raise AuthorizationError

    try:
        return account_id, webauthn.verify_registration_response(
            credential=credential,
            expected_challenge=unpadded_urlsafe_b64decode(challenge.sub),
            expected_rp_id=_origin_to_rp_id(challenge.org),
            expected_origin=challenge.org,
        )
    except InvalidRegistrationResponse as e:
        logger.debug(f"Invalid webauthn registration response: {e}")
        raise AuthorizationError


async def create_webauthn_registration(
    service: AuthService,
    config: Config,
    account: AccountEntity,
    registration: VerifiedRegistration,
    challenge: str,
) -> TokenResponse:
    """Create a WebAuthn registration.

    Args:
        service: The :class:`AuthService`.
        config: The server config.
        account: The account entity.
        registration: The verified WebAuthn registration.
        challenge: The challenge that was sent.

    Raises:
        AuthorizationError: If a challenge or credential was re-used.

    Returns:
        A :class:`TokenResponse`.
    """
    entity = await service.create_webauthn_registration(
        account,
        registration,
        challenge,
    )
    now = get_now()
    entity.date_last_used = now

    # remove any previously issued refresh tokens now that we have a better credential
    account.revoke_refresh_tokens()

    signed_refresh_token, refresh_token = await create_new_refresh_token(
        service,
        config,
        account,
        scopes=DEFAULT_SCOPES,  # TODO
    )

    signed_access_token, access_token = _create_access_token_from_refresh_token(
        config, account, refresh_token
    )

    return TokenResponse(
        access_token=signed_access_token,
        expires_in=int((access_token.exp - now).total_seconds()),
        refresh_token=signed_refresh_token,
        scope=join_scope(access_token.scope),
    )


async def get_webauthn_authentication_challenge(
    service: AuthService,
    config: Config,
    credential_id: str,
    origin: str,
) -> tuple[str, dict]:
    """Get a WebAuthn authentication challenge.

    Args:
        service: The :class:`AuthService`.
        config: The server config.
        credential_id: The credential ID as a base64-encoded string.
        origin: The origin.
    """
    if origin not in config.auth.allowed_auth_origins:
        logger.debug(f"Origin not allowed: {origin}")
        raise AuthorizationError

    # Convert from base64 to hex
    credential_id_hex = unpadded_urlsafe_b64decode(credential_id).hex()

    credential = await service.get_credential(credential_id_hex)
    if not credential:
        raise AuthorizationError

    allowed_credential = PublicKeyCredentialDescriptor(
        id=unpadded_urlsafe_b64decode(credential_id)
    )

    challenge_bytes = secrets.token_bytes(16)

    options = generate_authentication_options(
        rp_id=_origin_to_rp_id(origin),
        challenge=challenge_bytes,
        allow_credentials=[allowed_credential],
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    challenge = WebAuthnAuthenticationChallenge.create(
        account_id=credential.account_id,
        challenge_bytes=challenge_bytes,
        origin=origin,
    )

    return (
        challenge.encode(key=config.auth.signing_key),
        options.dict(by_alias=True, exclude_unset=False, exclude_none=True),
    )


async def verify_webauthn_authentication_response(
    service: AuthService,
    config: Config,
    challenge_data: str,
    response_data: str,
    origin: str,
) -> TokenResponse:
    """Verify a WebAuthn authentication response.

    Args:
        service: The :class:`AuthService`.
        config: The server config.
        challenge_data: The challenge data.
        response_data: The response data.
        origin: The origin.
    """
    if origin not in config.auth.allowed_auth_origins:
        logger.debug(f"Origin not allowed: {origin}")
        raise AuthorizationError

    try:
        challenge = WebAuthnAuthenticationChallenge.decode(
            challenge_data,
            key=config.auth.signing_key,
            issuer=None,  # these are not used
            audience=None,
        )
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid webauthn auth challenge: {e}")
        raise AuthorizationError

    if challenge.org != origin:
        logger.debug(f"Origin mismatch: {origin} != {challenge.org}")
        raise AuthorizationError

    try:
        credential = AuthenticationCredential.parse_raw(response_data)
    except pydantic.ValidationError:
        logger.debug("Invalid authentication credential")
        raise AuthorizationError

    account = await service.get_account(
        UUID(challenge.acc), lock=True, with_credentials=True
    )
    if not account:
        raise AuthorizationError

    credential_id_hex = unpadded_urlsafe_b64decode(credential.id).hex()
    credential_entity = _get_credential(account, credential_id_hex)

    public_key = unpadded_urlsafe_b64decode(
        credential_entity.data["registration"]["credentialPublicKey"]
    )

    sign_count = credential_entity.data["registration"]["signCount"]

    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=unpadded_urlsafe_b64decode(challenge.sub),
            expected_rp_id=_origin_to_rp_id(origin),
            expected_origin=origin,
            credential_public_key=public_key,
            credential_current_sign_count=sign_count,
            require_user_verification=True,
        )
    except InvalidAuthenticationResponse as e:
        logger.debug(f"Invalid webauthn authentication response: {e}")
        raise AuthorizationError

    refresh_token_id = unpadded_urlsafe_b64decode(challenge.sub).hex()
    _check_auth_challenge_reuse(account, challenge.sub)

    now = get_now()

    signed_refresh_token, refresh_token = await create_new_refresh_token(
        service,
        config,
        account,
        scopes=DEFAULT_SCOPES,  # TODO
        credential_id=refresh_token_id,
    )
    signed_access_token, access_token = _create_access_token_from_refresh_token(
        config, account, refresh_token
    )
    exp_t = int((refresh_token.exp - now).total_seconds())

    credential_entity.date_last_used = now
    new_data = copy.deepcopy(credential_entity.data)
    new_data["registration"]["signCount"] = verified.new_sign_count
    credential_entity.data = new_data

    return TokenResponse(
        access_token=signed_access_token,
        expires_in=exp_t,
        refresh_token=signed_refresh_token,
        scope=join_scope(access_token.scope),
    )


async def create_new_refresh_token(
    service: AuthService,
    config: Config,
    account: AccountEntity,
    scopes: Iterable[str],
    expiration_date: Optional[datetime] = None,
    credential_id: Optional[str] = None,
) -> tuple[str, RefreshToken]:
    """Create a new refresh token.

    Adds the new credential to the ``account``.

    Args:
        service: The :class:`AuthService`.
        config: The server configuration.
        account: The account entity.
        scopes: Scopes for the token.
        expiration_date: A non-default expiration date.

    Returns:
        A pair of the signed token string, and the :class:`RefreshToken` object.
    """
    credential_id = credential_id or secrets.token_hex(16)

    token = RefreshToken.create(
        account_id=account.id,
        credential_id=credential_id,
        token_num=1,
        scopes=scopes,
        expiration_date=expiration_date,
    )
    signed = token.encode(key=config.auth.signing_key)

    await service.create_refresh_token(account, token)
    return signed, token


def _create_access_token_from_refresh_token(
    config: Config,
    account: AccountEntity,
    refresh_token: RefreshToken,
) -> tuple[str, AccessToken]:
    """Create an access token from a refresh token."""
    access_token = AccessToken.create(
        account_id=account.id,
        email=account.email,
        scopes=refresh_token.scope,
    )
    signed_access_token = access_token.encode(key=config.auth.signing_key)
    return signed_access_token, access_token


def _origin_to_rp_id(origin: str) -> str:
    try:
        url_obj = URL(origin.encode())
        # only https: schemes are supported
        return url_obj.host.decode()
    except Exception:
        return ""


def _check_challenge_reuse(
    account: AccountEntity,
    challenge: str,
):
    """Check that a challenge was not re-used for account registration."""
    for cred in account.credentials:
        if cred.type == CredentialType.webauthn and cred.data["challenge"] == challenge:
            logger.debug(f"Webauthn registration challenge reused: {challenge}")
            raise AuthorizationError


def _check_auth_challenge_reuse(
    account: AccountEntity,
    challenge: str,
):
    """Check that an authentication challenge was not re-used."""
    challenge_hex = unpadded_urlsafe_b64decode(challenge).hex()
    for cred in account.credentials:
        if cred.id == challenge_hex:
            logger.debug(f"Webauthn authentication challenge reused: {challenge}")
            raise AuthorizationError


def _get_credential(
    account: AccountEntity,
    id: str,
) -> CredentialEntity:
    for cred in account.credentials:
        if cred.id == id:
            return cred
    else:
        logger.debug(f"Credential ID not found: {id}")
        raise AuthorizationError
