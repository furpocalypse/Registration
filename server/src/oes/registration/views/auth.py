"""Auth views."""
from typing import Optional
from uuid import UUID

from attrs import frozen
from blacksheep import FromForm, FromQuery, HTTPException, Request, allow_anonymous
from blacksheep.server.openapi.common import ResponseInfo
from loguru import logger
from oes.registration.app import app
from oes.registration.database import transaction
from oes.registration.docs import docs, docs_helper, serialize
from oes.registration.models.auth import AccessToken, TokenResponse, User, join_scope
from oes.registration.models.config import Config
from oes.registration.services.auth import (
    AuthorizationError,
    AuthService,
    create_new_account,
)
from oes.registration.services.auth import (
    create_webauthn_registration as _create_webauthn_registration,
)
from oes.registration.services.auth import (
    get_refresh_token_by_str,
    get_webauthn_authentication_challenge,
    get_webauthn_registration_challenge,
    update_refresh_token,
    verify_webauthn_authentication_response,
    verify_webauthn_registration_response,
)
from oes.registration.util import get_now
from oes.registration.views.parameters import AttrsBody
from sqlalchemy.ext.asyncio import AsyncSession


@frozen
class TokenRequest:
    grant_type: str
    refresh_token: str


@frozen
class CurrentAuthInfoResponse:
    id: UUID
    email: Optional[str]
    scope: str


@frozen
class WebAuthChallengeResponse:
    challenge: str
    options: dict


@frozen
class CreateWebAuthnRegistrationRequest:
    challenge: str
    result: str


@frozen
class WebAuthnAuthenticationRequest:
    challenge: str
    result: str


@allow_anonymous()
@app.router.get("/auth/current")
@docs_helper(
    response_type=CurrentAuthInfoResponse,
    response_summary="The current authentication info",
    tags=["Auth"],
)
async def get_current_auth_info(
    user: Optional[User],
):
    """Get the current authentication information."""
    if user is None:
        # TODO: correct error response formats
        raise HTTPException(401)

    return CurrentAuthInfoResponse(
        id=user.id,
        email=user.email,
        scope=join_scope(user.scope),
    )


@allow_anonymous()
@app.router.post("/auth/new-account")
@docs_helper(
    response_type=TokenResponse,
    response_summary="The token response",
    tags=["Auth"],
)
@transaction
async def get_new_account(
    service: AuthService,
    config: Config,
):
    """Get a new account."""
    token_response = await create_new_account(service, config)
    return token_response


async def handle_refresh_token(
    service: AuthService,
    config: Config,
    db: AsyncSession,
    refresh_token: str,
):
    result = await get_refresh_token_by_str(service, config, refresh_token, lock=True)
    if not result:
        # TODO: correct error response formats
        raise HTTPException(401)

    provided_token, current_token, entity = result
    _, provided_num = provided_token.token_info
    _, current_num = current_token.token_info

    if provided_num != current_num:
        # A superseded token was re-used
        logger.warning(f"A refresh token was re-used for {entity.account}")
        entity.account.revoke_refresh_tokens()
        await db.commit()
        raise HTTPException(401)
    else:
        now = get_now()
        new_token_str, new_token = update_refresh_token(config, entity)

        access_token = AccessToken.create(
            account_id=entity.account_id,
            email=entity.account.email,
            scopes=new_token.scope,
        )

        signed_access_token = access_token.encode(key=config.auth.signing_key)

        exp_t = int((access_token.exp - now).total_seconds())
        response = TokenResponse(
            access_token=signed_access_token,
            expires_in=exp_t,
            refresh_token=new_token_str,
            scope=join_scope(new_token.scope),
        )
        await db.commit()
        return response


@allow_anonymous()
@app.router.post("/auth/token")
@docs_helper(
    response_type=TokenResponse,
    response_summary="The token response",
    tags=["Auth"],
)
async def get_token(
    body: FromForm[TokenRequest],
    service: AuthService,
    config: Config,
    db: AsyncSession,
):
    """Get an access token."""
    if body.value.grant_type == "refresh_token":
        return await handle_refresh_token(service, config, db, body.value.refresh_token)
    else:
        # TODO: correct error response formats
        raise HTTPException(401)


@app.router.get("/auth/webauthn/register")
@docs(
    responses={
        200: ResponseInfo(
            "The WebAuthn registration challenge",
        )
    },
    tags=["Auth"],
)
@serialize(WebAuthChallengeResponse)
@transaction
async def get_webauthn_challenge(
    request: Request,
    service: AuthService,
    config: Config,
    user: User,
):
    """Get a WebAuthn registration challenge."""
    account = await service.get_account(user.id, lock=True, with_credentials=True)
    if not account:
        raise HTTPException(401)

    # TODO: ensure origin is one of a set of allowed values for auth
    origin = (request.get_first_header(b"Origin") or b"").decode()

    challenge_str, options = get_webauthn_registration_challenge(
        config,
        account_id=account.id,
        user_name=user.email or "Guest",  # TODO
        origin=origin,
    )

    return WebAuthChallengeResponse(challenge=challenge_str, options=options)


@app.router.post("/auth/webauthn/register")
@docs(
    responses={
        200: ResponseInfo(
            "The token response",
        )
    },
    tags=["Auth"],
)
@serialize(TokenResponse)
@transaction
async def create_webauthn_registration(
    request: Request,
    body: AttrsBody[CreateWebAuthnRegistrationRequest],
    service: AuthService,
    config: Config,
    user: User,
):
    """Create a WebAuthn registration."""

    origin = (request.get_first_header(b"Origin") or b"").decode()

    try:
        account_id, verified = verify_webauthn_registration_response(
            config,
            body.value.challenge,
            body.value.result,
            origin,
        )
    except AuthorizationError:
        raise HTTPException(401)

    account = await service.get_account(account_id, lock=True, with_credentials=True)
    if not account or account.id != user.id:
        raise HTTPException(401)

    try:
        return await _create_webauthn_registration(
            service,
            config,
            account,
            verified,
            body.value.challenge,
        )
    except AuthorizationError:
        raise HTTPException(401)


@allow_anonymous()
@app.router.get("/auth/webauthn")
@docs(
    responses={
        200: ResponseInfo(
            "The WebAuthn authentication challenge",
        )
    },
    tags=["Auth"],
)
@serialize(WebAuthChallengeResponse)
async def get_webauthn_auth_challenge(
    request: Request,
    credential_id: FromQuery[str],
    service: AuthService,
    config: Config,
):
    """Get a WebAuthn authentication challenge."""
    origin = (request.get_first_header(b"Origin") or b"").decode()

    try:
        challenge, options = await get_webauthn_authentication_challenge(
            service,
            config,
            credential_id.value,
            origin,
        )
    except AuthorizationError:
        raise HTTPException(401)

    return WebAuthChallengeResponse(challenge, options)


@allow_anonymous()
@app.router.post("/auth/webauthn")
@docs(
    responses={
        200: ResponseInfo(
            "The WebAuthn authentication challenge",
        )
    },
    tags=["Auth"],
)
@serialize(TokenResponse)
async def complete_webauthn_auth_challenge(
    request: Request,
    body: AttrsBody[WebAuthnAuthenticationRequest],
    service: AuthService,
    config: Config,
):
    """Complete WebAuthn authentication."""
    origin = (request.get_first_header(b"Origin") or b"").decode()

    try:
        return await verify_webauthn_authentication_response(
            service,
            config,
            body.value.challenge,
            body.value.result,
            origin,
        )
    except AuthorizationError:
        raise HTTPException(401)
