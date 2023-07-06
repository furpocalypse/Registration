"""OAuth views."""
import asyncio

from attrs import frozen
from blacksheep import Content, FromForm, Request, Response, allow_anonymous
from blacksheep.exceptions import BadRequest, Forbidden, NotFound
from blacksheep.server.openapi.common import RequestBodyInfo
from loguru import logger
from oes.registration.app import app
from oes.registration.auth.account_service import AccountService
from oes.registration.auth.credential_service import (
    CredentialService,
    create_new_refresh_token,
    create_refresh_token_entity,
)
from oes.registration.auth.models import CredentialType
from oes.registration.auth.oauth.validator import CustomServer
from oes.registration.auth.scope import DEFAULT_SCOPES
from oes.registration.auth.token import WEBAUTHN_REFRESH_TOKEN_LIFETIME, TokenResponse
from oes.registration.auth.user import User
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


@allow_anonymous()
@app.router.post("/auth/account/create")
@docs_helper(
    response_type=TokenResponse,
    tags=["Account"],
)
@transaction
async def new_account_endpoint(
    account_service: AccountService,
    credential_service: CredentialService,
    config: Config,
) -> TokenResponse:
    """Create a new account, without credentials."""
    new_account = await account_service.create_account(None)
    user = User(
        {
            "id": new_account.id,
            "email": new_account.email,
            # TODO: when to get default scopes?
            "scope": DEFAULT_SCOPES,
        }
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

    user = User(
        {
            "id": account.id,
            "email": account.email,
            "scope": DEFAULT_SCOPES,
        }
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


@allow_anonymous()
@app.router.get("/auth/webauthn/authenticate/{credential_id}")
@docs_helper(
    response_type=WebAuthnChallengeResponse,
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
    user = User(
        {
            "id": account.id,
            "email": account.email,
            "scope": DEFAULT_SCOPES,
        }
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
