"""WebAuthn module."""
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Literal, Optional
from uuid import UUID

import jwt
import pydantic
import webauthn
from attrs import frozen
from oes.registration.auth.account_service import AccountService
from oes.registration.auth.credential_service import CredentialService
from oes.registration.auth.entities import AccountEntity, CredentialEntity
from oes.registration.auth.models import CredentialType
from oes.registration.auth.token import TokenBase
from oes.registration.models.config import AuthConfig
from oes.registration.util import (
    get_now,
    origin_to_rp_id,
    unpadded_urlsafe_b64decode,
    unpadded_urlsafe_b64encode,
)
from typing_extensions import Self
from webauthn.helpers.exceptions import (
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticationCredential,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialCreationOptions,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRequestOptions,
    RegistrationCredential,
    ResidentKeyRequirement,
)

WEBAUTHN_REGISTRATION_LIFETIME = timedelta(seconds=180)
WEBAUTHN_AUTHENTICATION_LIFETIME = timedelta(seconds=180)


class WebAuthnError(ValueError):
    """Raised when a WebAuthn error occurs."""

    pass


@frozen(kw_only=True)
class WebAuthnRegistrationChallenge(TokenBase):
    """Signed WebAuthn registration challenge."""

    typ: Literal["wr"]
    exp: datetime

    sub: str
    """The challenge data."""

    acc: str
    """The account ID."""

    rp: str
    """The relying party."""

    @classmethod
    def create(
        cls,
        rp_id: str,
        rp_name: str,
        user_name: Optional[str] = None,
        expiration_date: Optional[datetime] = None,
    ) -> tuple[Self, PublicKeyCredentialCreationOptions]:
        """Create a WebAuthn registration request.

        Args:
            rp_id: The ID of the relying party.
            rp_name: The name of the relying party.
            user_name: The name of the user.
            expiration_date: A non-default expiration date.
        """
        account_id = uuid.uuid4()
        challenge_bytes = secrets.token_bytes(16)
        opts = webauthn.generate_registration_options(
            rp_id=rp_id,
            rp_name=rp_name,
            user_id=account_id.hex,
            user_name=user_name or "Guest",
            challenge=challenge_bytes,
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.DISCOURAGED,
            ),
            timeout=int(WEBAUTHN_REGISTRATION_LIFETIME.total_seconds()) * 1000,
        )

        token = cls(
            typ="wr",
            sub=unpadded_urlsafe_b64encode(challenge_bytes),
            acc=account_id.hex,
            rp=rp_id,
            exp=expiration_date
            if expiration_date is not None
            else (get_now() + WEBAUTHN_REGISTRATION_LIFETIME),
        )
        return token, opts


@frozen(kw_only=True)
class WebAuthnAuthenticationChallenge(TokenBase):
    """Signed WebAuthn authentication challenge."""

    typ: Literal["wa"]
    exp: datetime

    sub: str
    """The challenge data."""

    cr: str
    """The credential ID."""

    rp: str
    """The relying party."""

    @classmethod
    def create(
        cls,
        rp_id: str,
        credential_id: str,
        expiration_date: Optional[datetime] = None,
    ) -> tuple[Self, PublicKeyCredentialRequestOptions]:
        """Create a WebAuthn authentication challenge.

        Args:
            rp_id: The ID of the relying party.
            credential_id: The credential ID.
            expiration_date: A non-default expiration date.
        """
        challenge_bytes = secrets.token_bytes(16)

        opts = webauthn.generate_authentication_options(
            rp_id=rp_id,
            challenge=challenge_bytes,
            timeout=int(WEBAUTHN_AUTHENTICATION_LIFETIME.total_seconds()) * 1000,
            allow_credentials=[
                PublicKeyCredentialDescriptor(
                    id=unpadded_urlsafe_b64decode(credential_id),
                )
            ],
        )

        token = cls(
            typ="wa",
            sub=unpadded_urlsafe_b64encode(challenge_bytes),
            cr=credential_id,
            rp=rp_id,
            exp=expiration_date
            if expiration_date is not None
            else (get_now() + WEBAUTHN_AUTHENTICATION_LIFETIME),
        )
        return token, opts


def validate_webauthn_registration(
    challenge_data: str,
    response_data: str,
    origin: str,
    auth_config: AuthConfig,
) -> CredentialEntity:
    """Verify a registration response.

    Args:
        challenge_data: The challenge data.
        response_data: The raw response data.
        origin: The origin of the request.
        auth_config: The auth config.

    Raises:
        WebAuthnError: If the validation fails.

    Returns:
        A :class:`CredentialEntity`.
    """
    if origin not in auth_config.allowed_auth_origins:
        raise WebAuthnError("Origin not allowed")

    try:
        challenge = WebAuthnRegistrationChallenge.decode(
            challenge_data, key=auth_config.signing_key
        )
    except jwt.InvalidTokenError:
        raise WebAuthnError("Invalid challenge")

    rp_id = origin_to_rp_id(origin)
    if rp_id != challenge.rp:
        raise WebAuthnError("Invalid origin")

    account_id = UUID(challenge.acc)

    try:
        credential = RegistrationCredential.parse_raw(response_data)
    except pydantic.ValidationError:
        raise WebAuthnError("Invalid credential")

    try:
        verified = webauthn.verify_registration_response(
            credential=credential,
            expected_challenge=unpadded_urlsafe_b64decode(challenge.sub),
            expected_rp_id=rp_id,
            expected_origin=origin,
        )
    except InvalidRegistrationResponse:
        raise WebAuthnError("Invalid registration response")

    credential_entity = CredentialEntity(
        id=unpadded_urlsafe_b64encode(verified.credential_id),
        account_id=account_id,
        type=CredentialType.webauthn,
        date_created=get_now(),
        data=verified.dict(by_alias=True),
    )

    return credential_entity


async def create_webauthn_account(
    credential_entity: CredentialEntity,
    account_service: AccountService,
    credential_service: CredentialService,
) -> AccountEntity:
    """Create an account from a WebAuthn credential.

    Args:
        credential_entity: The :class:`CredentialEntity`.
        account_service: The :class:`AccountService`.
        credential_service: The :class:`CredentialService`.

    Returns:
        The created :class:`AccountEntity`.

    Raises:
        WebAuthnError: If the account or credential already exist.
    """
    account = await account_service.get_account(credential_entity.account_id)
    if account is not None:
        raise WebAuthnError("Account already exists")

    cur_credential = await credential_service.get_credential(credential_entity.id)
    if cur_credential is not None:
        raise WebAuthnError("Credential is already registered")

    account = await account_service.create_account(
        None, id=credential_entity.account_id
    )
    account.credentials.append(credential_entity)
    return account


async def validate_webauthn_authentication(
    challenge_data: str,
    response_data: str,
    origin: str,
    credential_service: CredentialService,
    auth_config: AuthConfig,
) -> UUID:
    """Validate a WebAuthn authentication response.

    Updates the :class:`CredentialEntity` with the new ``signCount``.

    Args:
        challenge_data: The signed challenge data.
        response_data: The response from the authenticator.
        origin: The origin.
        credential_service: The :class:`CredentialService`.
        auth_config: The :class:`AuthConfig`.

    Returns:
        The account ID.

    Raises:
        WebAuthnError: If the authentication fails.
    """
    if origin not in auth_config.allowed_auth_origins:
        raise WebAuthnError("Origin not allowed")

    try:
        challenge = WebAuthnAuthenticationChallenge.decode(
            challenge_data, key=auth_config.signing_key
        )
    except jwt.InvalidTokenError:
        raise WebAuthnError("Invalid challenge")

    try:
        credential = AuthenticationCredential.parse_raw(response_data)
    except pydantic.ValidationError:
        raise WebAuthnError("Invalid credential")

    rp_id = origin_to_rp_id(origin)
    if rp_id != challenge.rp:
        raise WebAuthnError("Invalid origin")

    credential_entity = await credential_service.get_credential(challenge.cr, lock=True)
    if credential_entity is None:
        raise WebAuthnError("Unknown credential")

    credential_data = dict(credential_entity.data)

    public_key = unpadded_urlsafe_b64decode(credential_data["credentialPublicKey"])
    sign_count = credential_data["signCount"]

    try:
        verified = webauthn.verify_authentication_response(
            credential=credential,
            expected_challenge=unpadded_urlsafe_b64decode(challenge.sub),
            expected_rp_id=origin_to_rp_id(origin),
            expected_origin=origin,
            credential_public_key=public_key,
            credential_current_sign_count=sign_count,
            require_user_verification=True,
        )
    except InvalidAuthenticationResponse:
        raise WebAuthnError("Invalid authentication response")

    credential_entity.date_last_used = get_now()
    credential_data["signCount"] = verified.new_sign_count
    credential_entity.data = credential_data
    return credential_entity.account_id
