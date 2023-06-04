"""Self-service views."""
import uuid
from typing import Optional

from blacksheep import FromQuery
from oes.registration.app import app
from oes.registration.docs import docs_helper
from oes.registration.models.event import EventConfig
from oes.registration.services.registration import (
    RegistrationService,
    get_allowed_add_interviews,
    get_allowed_change_interviews,
    render_self_service_registration,
)
from oes.registration.util import check_not_found
from oes.registration.views.responses import (
    InterviewOption,
    SelfServiceRegistrationListResponse,
    SelfServiceRegistrationResponse,
)


@app.router.get("/self-service/registrations")
@docs_helper(
    response_type=SelfServiceRegistrationListResponse,
    response_summary="The list of self service registrations",
    tags=["Self-Service"],
)
async def list_self_service_registration(
    event_id: FromQuery[Optional[str]],
    # TODO: account ID
    service: RegistrationService,
    event_config: EventConfig,
) -> SelfServiceRegistrationListResponse:
    """List self-service registrations."""
    if event_id.value:
        event = check_not_found(event_config.get_event(event_id.value))
        add_options = get_allowed_add_interviews(event)
    else:
        add_options = []

    # TODO: permissions

    registrations = await service.list_self_service_registrations(
        uuid.uuid4(),  # TODO: account ID
        event_id=event_id.value,
    )

    results = []

    for reg in registrations:
        event = event_config.get_event(reg.event_id)
        # TODO: check event visibility
        if event:
            change_options = get_allowed_change_interviews(event, reg)
            model = render_self_service_registration(event, reg)
            results.append(
                SelfServiceRegistrationResponse(
                    model, [InterviewOption(o.id, o.name) for o in change_options]
                )
            )

    return SelfServiceRegistrationListResponse(
        results, [InterviewOption(o.id, o.name) for o in add_options]
    )
