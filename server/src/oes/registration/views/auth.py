"""OAuth views."""
import asyncio
import re
from typing import Optional
from uuid import UUID

import jwt
from attrs import frozen
from blacksheep import (
    Content,
    FromForm,
    HTTPException,
    Request,
    Response,
    allow_anonymous,
)
from blacksheep.exceptions import BadRequest, Forbidden, NotFound
from blacksheep.server.openapi.common import RequestBodyInfo, ResponseInfo
from loguru import logger
from oes.registration.app import app
from oes.registration.auth.account_service import AccountService
from oes.registration.auth.credential_service import (
    CredentialService,
    create_new_refresh_token,
    create_refresh_token_entity,
)
from oes.registration.auth.email_auth_service import EmailAuthService, send_auth_code
from oes.registration.auth.models import CredentialType
from oes.registration.auth.oauth.validator import CustomServer
from oes.registration.auth.scope import DEFAULT_SCOPES
from oes.registration.auth.token import (
    WEBAUTHN_REFRESH_TOKEN_LIFETIME,
    TokenResponse,
    VerifiedEmailToken,
)
from oes.registration.auth.user import User, UserIdentity
from oes.registration.auth.webauthn import (
    WebAuthnAuthenticationChallenge,
    WebAuthnError,
    WebAuthnRegistrationChallenge,
    create_webauthn_account,
    validate_webauthn_authentication,
    validate_webauthn_registration,
)
from oes.registration.database import transaction
from oes.registration.docs import docs, docs_helper
from oes.registration.models.config import Config
from oes.registration.util import check_not_found, get_now, get_origin, origin_to_rp_id
from oes.registration.views.parameters import AttrsBody
from sqlalchemy.ext.asyncio import AsyncSession


@frozen
class AccountInfoResponse:
    """Account info."""

    id: Optional[UUID] = None
    email: Optional[str] = None
    scope: str = ""


@frozen
class EmailVerificationBody:
    """An email verification request."""

    email: str


@frozen
class EmailVerificationCodeBody:
    """An email verification code."""

    email: str
    code: str


@frozen
class EmailVerificationTokenBody:
    """An email verification token result."""

    token: str


@frozen
class NewAccountBody:
    """A request body to create a new account."""

    email_token: Optional[str] = None


@frozen
class WebAuthnChallengeResponse:
    """A WebAuthn challenge."""

    challenge: str
    options: dict


@frozen
class WebAuthnChallengeResult:
    """A completed WebAuthn challenge."""

    challenge: str
    result: str
    email_token: Optional[str] = None


@app.router.get("/auth/account")
@docs_helper(
    response_type=AccountInfoResponse,
    response_summary="The account information",
    tags=["Account"],
)
async def get_account_info(user: User) -> AccountInfoResponse:
    """Get the current account info."""
    return AccountInfoResponse(
        id=user.id,
        email=user.email,
        scope=str(user.scope),
    )


@allow_anonymous()
@app.router.post("/auth/email/send")
@docs(
    responses={
        204: ResponseInfo(
            "The email was sent.",
        ),
    },
    tags=["Account"],
)
@transaction
async def send_email_verification(
    body: AttrsBody[EmailVerificationBody],
    email_auth_service: EmailAuthService,
    config: Config,
) -> Response:
    """Send an email verification code."""
    email = body.value.email.strip()
    if not re.match(r"^.+@.+\..+$", email):
        raise HTTPException(422, "Invalid email")
    await send_auth_code(email_auth_service, config.hooks, email)
    return Response(204)


@allow_anonymous()
@app.router.post("/auth/email/verify")
@docs_helper(
    response_type=EmailVerificationTokenBody,
    response_summary="The verified email token",
    tags=["Account"],
)
async def verify_email(
    body: AttrsBody[EmailVerificationCodeBody],
    email_auth_service: EmailAuthService,
    config: Config,
    db: AsyncSession,
) -> EmailVerificationTokenBody:
    """Verify an email address."""
    email = body.value.email.strip()
    code = re.sub(r"[^a-zA-Z0-9]+", "", body.value.code)
    entity = await email_auth_service.get_auth_code_for_email(email)
    if not entity or not entity.get_is_usable():
        raise Forbidden
    elif code != entity.code:
        entity.attempts += 1
        await db.commit()
        raise Forbidden
    else:
        token = VerifiedEmailToken.create(email).encode(key=config.auth.signing_key)
        await email_auth_service.delete_code(entity)
        await db.commit()
        return EmailVerificationTokenBody(token=token)


@allow_anonymous()
@app.router.post("/auth/account/create")
@docs_helper(
    response_type=TokenResponse,
    response_summary="The token response for the new account",
    tags=["Account"],
)
@transaction
async def new_account_endpoint(
    account_service: AccountService,
    credential_service: CredentialService,
    config: Config,
    body: Optional[AttrsBody[NewAccountBody]] = None,
) -> TokenResponse:
    """Create a new account, without credentials."""
    email = _verify_email_token(body.value.email_token if body else None, config)
    new_account = await account_service.create_account(email)
    user = UserIdentity(
        id=new_account.id,
        email=new_account.email,
        scope=DEFAULT_SCOPES,
    )

    refresh_token = create_new_refresh_token(user)
    refresh_token_entity = create_refresh_token_entity(refresh_token)
    await credential_service.create_credential(refresh_token_entity)

    now = get_now(seconds_only=True)
    access_token = refresh_token.create_access_token()
    expires_in = int((access_token.exp - now).total_seconds())

    return TokenResponse.create(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        key=config.auth.signing_key,
    )


@allow_anonymous()
@app.router.get("/auth/webauthn/register")
@docs_helper(
    response_type=WebAuthnChallengeResponse,
    response_summary="The registration challenge",
    tags=["Account"],
)
async def get_webauthn_registration_challenge(
    request: Request,
    config: Config,
) -> WebAuthnChallengeResponse:
    """Get a WebAuthn registration challenge."""
    origin = get_origin(request)

    if origin not in config.auth.allowed_auth_origins:
        raise Forbidden

    challenge, opts = WebAuthnRegistrationChallenge.create(
        rp_id=origin_to_rp_id(origin),
        rp_name=config.auth.name,
    )

    return WebAuthnChallengeResponse(
        challenge=challenge.encode(key=config.auth.signing_key),
        options=opts.dict(by_alias=True, exclude_none=True),
    )


@allow_anonymous()
@app.router.post("/auth/webauthn/register")
@docs_helper(
    response_type=TokenResponse,
    response_summary="The token response for the new account",
    tags=["Account"],
)
@transaction
async def complete_webauthn_registration(
    request: Request,
    body: AttrsBody[WebAuthnChallengeResult],
    config: Config,
    account_service: AccountService,
    credential_service: CredentialService,
) -> TokenResponse:
    """Complete a WebAuthn registration."""
    origin = get_origin(request)

    try:
        credential_entity = validate_webauthn_registration(
            body.value.challenge,
            body.value.result,
            origin,
            config.auth,
        )

        account = await create_webauthn_account(
            credential_entity, account_service, credential_service
        )
    except WebAuthnError as e:
        logger.debug(f"WebAuthn registration failed: {e}")
        raise BadRequest

    email = _verify_email_token(body.value.email_token, config)
    account.email = email

    user = UserIdentity(
        id=account.id,
        email=account.email,
        scope=DEFAULT_SCOPES,
    )

    now = get_now(seconds_only=True)
    exp = now + WEBAUTHN_REFRESH_TOKEN_LIFETIME
    refresh_token = create_new_refresh_token(user, expiration_date=exp)
    refresh_token_entity = create_refresh_token_entity(refresh_token)
    await credential_service.create_credential(refresh_token_entity)
    access_token = refresh_token.create_access_token()

    return TokenResponse.create(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(WEBAUTHN_REFRESH_TOKEN_LIFETIME.total_seconds()),
        key=config.auth.signing_key,
    )


def _verify_email_token(token: Optional[str], config: Config) -> Optional[str]:
    if not token:
        return None

    try:
        decoded = VerifiedEmailToken.decode(token, key=config.auth.signing_key)
        return decoded.email
    except jwt.InvalidTokenError:
        return None


@allow_anonymous()
@app.router.get("/auth/webauthn/authenticate/{credential_id}")
@docs_helper(
    response_type=WebAuthnChallengeResponse,
    response_summary="The authentication challenge",
    tags=["Account"],
)
async def get_webauthn_authentication_challenge(
    credential_id: str,
    request: Request,
    credential_service: CredentialService,
    config: Config,
) -> WebAuthnChallengeResponse:
    """Get a WebAuthn authentication challenge."""
    origin = get_origin(request)
    if origin not in config.auth.allowed_auth_origins:
        raise Forbidden

    entity = check_not_found(
        await credential_service.get_credential(credential_id.rstrip("="))
    )
    if entity.type != CredentialType.webauthn:
        raise NotFound

    challenge, opts = WebAuthnAuthenticationChallenge.create(
        rp_id=origin_to_rp_id(origin),
        credential_id=entity.id,
    )

    return WebAuthnChallengeResponse(
        challenge=challenge.encode(key=config.auth.signing_key),
        options=opts.dict(by_alias=True, exclude_none=True),
    )


@allow_anonymous()
@app.router.post("/auth/webauthn/authenticate")
@docs_helper(
    response_type=TokenResponse,
    response_summary="The token response",
    tags=["Account"],
)
@transaction
async def complete_webauthn_authentication(
    request: Request,
    body: AttrsBody[WebAuthnChallengeResult],
    account_service: AccountService,
    credential_service: CredentialService,
    config: Config,
) -> TokenResponse:
    """Complete a WebAuthn authentication challenge."""
    origin = get_origin(request)

    try:
        account_id = await validate_webauthn_authentication(
            challenge_data=body.value.challenge,
            response_data=body.value.result,
            origin=origin,
            credential_service=credential_service,
            auth_config=config.auth,
        )
    except WebAuthnError as e:
        logger.debug(f"WebAuthn authentication failed: {e}")
        raise Forbidden

    account = check_not_found(
        await account_service.get_account(account_id, with_credentials=True)
    )
    user = UserIdentity(
        id=account.id,
        email=account.email,
        scope=DEFAULT_SCOPES,
    )

    now = get_now(seconds_only=True)
    exp = now + WEBAUTHN_REFRESH_TOKEN_LIFETIME

    refresh_token = create_new_refresh_token(
        user,
        expiration_date=exp,
    )
    refresh_token_entity = create_refresh_token_entity(refresh_token)
    await credential_service.create_credential(refresh_token_entity)
    access_token = refresh_token.create_access_token()

    return TokenResponse.create(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(WEBAUTHN_REFRESH_TOKEN_LIFETIME.total_seconds()),
        key=config.auth.signing_key,
    )


@allow_anonymous()
@app.router.post(
    "/auth/token",
)
@docs(
    request_body=RequestBodyInfo(
        examples={
            "refresh_token": {
                "client_id": "oes",
                "grant_type": "refresh_token",
                "refresh_token": "...",
            }
        }
    ),
    responses={200: ResponseInfo("The token response")},
    tags=["OAuth"],
)
@transaction
async def token_endpoint(
    request: Request,
    form: FromForm,
    config: Config,
    account_service: AccountService,
    credential_service: CredentialService,
) -> Response:
    """Token endpoint for OAuth."""
    loop = asyncio.get_running_loop()
    server = CustomServer(config.auth, account_service, credential_service, loop)
    headers = {k.decode(): v.decode() for k, v in request.headers.items()}

    resp_headers, resp_body, resp_status = await asyncio.to_thread(
        server.create_token_response,
        str(request.url),
        "POST",
        form.value,
        headers,
    )

    response = Response(
        resp_status,
        [(k.encode(), v.encode()) for k, v in resp_headers.items()],
        Content(b"application/json", resp_body.encode()),
    )
    return response
