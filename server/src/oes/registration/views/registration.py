"""Registration views."""
from typing import Optional, Union
from uuid import UUID

from attrs import Factory, field, frozen
from blacksheep import Content, HTTPException, Request, Response, auth
from blacksheep.server.openapi.common import (
    ContentInfo,
    ParameterInfo,
    ParameterSource,
    ResponseInfo,
)
from oes.registration.app import app
from oes.registration.auth import RequireAdmin
from oes.registration.database import transaction
from oes.registration.docs import docs, docs_helper
from oes.registration.entities.registration import RegistrationEntity
from oes.registration.log import AuditLogType, audit_log
from oes.registration.models.event import EventConfig
from oes.registration.models.registration import (
    Registration,
    RegistrationState,
    WritableRegistration,
)
from oes.registration.serialization import get_converter
from oes.registration.serialization.json import json_loads
from oes.registration.services.registration import RegistrationService
from oes.registration.util import check_not_found
from oes.registration.views.parameters import AttrsBody
from oes.registration.views.responses import RegistrationListResponse


@frozen(kw_only=True)
class CreateRegistrationRequest:
    """Request body to create a registration."""

    state: RegistrationState = RegistrationState.created
    event_id: str
    number: Optional[int] = None
    option_ids: set[str] = field(default=Factory(lambda: set()))
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None


@frozen(kw_only=True)
class UpdateRegistrationRequest:
    """Request body to update a registration."""

    number: Optional[int] = None
    option_ids: set[str] = field(default=Factory(lambda: set()))
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None


@auth(RequireAdmin)
@app.router.get("/registrations")
@docs_helper(
    response_type=list[RegistrationListResponse],
    response_summary="The list of registrations",
    tags=["Registration"],
)
@transaction
async def list_registrations(
    reg: RegistrationService,
    page: int,
    per_page: int,
) -> list[Registration]:
    """Search registrations."""
    results = await reg.list_registrations(page=page, per_page=per_page)
    return [r.get_model() for r in results]


@auth(RequireAdmin)
@app.router.post("/registrations")
@docs(
    responses={
        200: ResponseInfo(
            "The created response",
        )
    },
    tags=["Registration"],
)
@transaction
async def create_registration(
    request: Request,
    body: AttrsBody[CreateRegistrationRequest],
    service: RegistrationService,
    event_config: EventConfig,
) -> Response:
    """Create a registration."""
    # TODO: permissions
    event = event_config.get_event(body.value.event_id)
    if not event:
        raise HTTPException(422, "Event ID not found")

    # should already be loaded
    body_json = await request.json(loads=json_loads)

    writable = get_converter().structure(body_json, WritableRegistration)

    entity = RegistrationEntity(
        state=body.value.state,
        event_id=event.id,
        number=writable.number,
        option_ids=list(writable.option_ids),
        email=writable.email,
        first_name=writable.first_name,
        last_name=writable.last_name,
        preferred_name=writable.preferred_name,
        extra_data=writable.extra_data,
    )

    await service.create_registration(entity)

    return registration_response(entity.get_model())


@auth(RequireAdmin)
@app.router.get("/registrations/{id}")
@docs(
    responses={
        200: ResponseInfo(
            "The registration",
            content=[ContentInfo(Registration)],
        )
    },
    tags=["Registration"],
)
async def read_registration(
    id: UUID,
    service: RegistrationService,
) -> Response:
    """Read a registration."""
    reg = check_not_found(await service.get_registration(id))

    # TODO: permissions
    return registration_response(reg.get_model())


@auth(RequireAdmin)
@app.router.put("/registrations/{id}")
@docs(
    parameters={
        "ETag": ParameterInfo(
            "The ETag of the current version of the registration",
            value_type=str,
            source=ParameterSource.HEADER,
            required=True,
            example='W/"asdf1234"',
        )
    },
    responses={
        200: ResponseInfo(
            "The updated registration",
            content=[ContentInfo(Registration)],
        )
    },
    tags=["Registration"],
)
@transaction
async def update_registration(
    request: Request,
    id: UUID,
    service: RegistrationService,
    _body: AttrsBody[CreateRegistrationRequest],
) -> Response:
    """Update a registration."""
    # TODO: permissions
    reg = check_not_found(await service.get_registration(id, lock=True))

    check_etag(request, reg)

    # should already be loaded
    body_json = await request.json(loads=json_loads)
    writable = get_converter().structure(body_json, WritableRegistration)
    reg.update_properties_from_model(writable)

    audit_log.bind(type=AuditLogType.registration_update).success(
        "Registration {registration} updated", registration=reg
    )

    return registration_response(reg.get_model())


@auth(RequireAdmin)
@app.router.put("/registrations/{id}/complete")
@docs(
    responses={
        200: ResponseInfo(
            "The updated registration",
            content=[ContentInfo(Registration)],
        )
    },
    tags=["Registration"],
)
@transaction
async def complete_registration(
    id: UUID,
    service: RegistrationService,
) -> Response:
    """Complete a pending registration."""
    reg = check_not_found(await service.get_registration(id, lock=True))

    # TODO: permissions

    try:
        reg.complete()
    except ValueError as e:
        raise HTTPException(409, str(e))

    return registration_response(reg.get_model())


@auth(RequireAdmin)
@app.router.put("/registrations/{id}/cancel")
@docs(
    responses={
        200: ResponseInfo(
            "The updated registration",
            content=[ContentInfo(Registration)],
        )
    },
    tags=["Registration"],
)
@transaction
async def cancel_registration(
    id: UUID,
    service: RegistrationService,
) -> Response:
    """Cancel a pending registration."""
    reg = check_not_found(await service.get_registration(id, lock=True))

    # TODO: permissions

    try:
        reg.cancel()
    except ValueError as e:
        raise HTTPException(409, str(e))

    return registration_response(reg.get_model())


# TODO: determine delete semantics


def check_etag(request: Request, reg: Union[Registration, RegistrationEntity]):
    """Check that the ETag matches, or raise :class:`HTTPException`."""
    header = request.headers.get_first(b"ETag")
    if not header:
        raise HTTPException(428)  # precondition required

    expected = get_etag(reg)
    if header != expected:
        raise HTTPException(412)  # precondition failed


def registration_response(reg: Registration) -> Response:
    """Return a JSON-encode :class:`Registration`.

    Sets the ``ETag`` header.
    """
    data = get_converter().dumps(reg)
    etag = get_etag(reg)
    return Response(
        200,
        headers=[
            (b"ETag", etag),
        ],
        content=Content(
            b"application/json",
            data,
        ),
    )


def get_etag(reg: Union[Registration, RegistrationEntity]) -> bytes:
    """Get the ETag for a registration's version."""
    return f'W/"{reg.version}"'.encode()
