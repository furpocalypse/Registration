"""Event views."""
from oes.registration.app import app
from oes.registration.docs import docs_helper
from oes.registration.models.event import EventConfig
from oes.registration.util import check_not_found
from oes.registration.views.responses import EventResponse


@app.router.get("/events")
@docs_helper(
    response_type=list[EventResponse],
    response_summary="The list of available events",
    tags=["Event"],
)
async def list_events(events: EventConfig):
    """List the available events."""
    return events.events


@app.router.get("/events/{event_id}")
@docs_helper(response_type=EventResponse, response_summary="The event", tags=["Event"])
async def read_event(
    event_id: str,
    event_config: EventConfig,
):
    """Get an event by ID."""
    event = check_not_found(event_config.get_event(event_id))
    return event
