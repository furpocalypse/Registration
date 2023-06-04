"""Access code views."""
from datetime import datetime
from typing import Optional

from attrs import frozen
from blacksheep import Response
from oes.registration.app import app
from oes.registration.database import transaction
from oes.registration.docs import docs, docs_helper
from oes.registration.models.access_code import AccessCodeSettings
from oes.registration.services.access_code import AccessCodeService
from oes.registration.util import check_not_found
from oes.registration.views.parameters import AttrsBody
from oes.registration.views.responses import AccessCodeListResponse, AccessCodeResponse


@frozen
class CreateAccessCodeRequest:
    """Request body for creating an access code."""

    event_id: str
    date_expires: datetime
    name: Optional[str]
    data: AccessCodeSettings


@app.router.get("/access-code")
@docs_helper(
    response_type=list[AccessCodeListResponse],
    response_summary="The access codes",
    tags=["Access Code"],
)
async def list_access_codes(
    service: AccessCodeService, event_id: Optional[str], page: int, per_page: int
) -> list[AccessCodeListResponse]:
    """List access codes."""
    # TODO: permissions
    results = await service.list_access_codes(
        event_id=event_id, page=page, per_page=per_page
    )

    return [
        AccessCodeListResponse(
            code=r.code,
            event_id=r.event_id,
            name=r.name,
            used=r.used,
        )
        for r in results
    ]


@app.router.post("/access-code")
@docs_helper(
    response_type=AccessCodeResponse,
    response_summary="The created access code",
    tags=["Access Code"],
)
@transaction
async def create_access_code(
    service: AccessCodeService,
    body: AttrsBody[CreateAccessCodeRequest],
) -> AccessCodeResponse:
    """Create an access code."""
    create = body.value
    result = await service.create_access_code(
        event_id=create.event_id,
        name=create.name,
        expiration_date=create.date_expires,
        settings=create.data,
    )

    return AccessCodeResponse.create(result)


@app.router.delete("/access-code/{code}")
@docs(tags=["Access Code"])
@transaction
async def delete_access_code(service: AccessCodeService, code: str) -> Response:
    """Delete an access code."""
    result = check_not_found(await service.get_access_code(code))
    await service.delete_access_code(result)
    return Response(204)
