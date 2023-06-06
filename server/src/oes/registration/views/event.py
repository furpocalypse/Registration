"""Event views."""
from collections.abc import Sequence

from blacksheep import auth
from blacksheep.exceptions import NotFound
from oes.registration.app import app
from oes.registration.auth import RequireEvent
from oes.registration.docs import docs_helper
from oes.registration.models.auth import User
from oes.registration.models.event import Event, EventConfig
from oes.registration.util import check_not_found
from oes.registration.views.responses import EventResponse


@auth(RequireEvent)
@app.router.get("/events")
@docs_helper(
    response_type=list[EventResponse],
    response_summary="The list of available events",
    tags=["Event"],
)
async def list_events(events: EventConfig, user: User) -> Sequence[Event]:
    """List the available events."""
    return [e for e in events.events if e.is_visible_to(user)]


@auth(RequireEvent)
@app.router.get("/events/{event_id}")
@docs_helper(response_type=EventResponse, response_summary="The event", tags=["Event"])
async def read_event(event_id: str, event_config: EventConfig, user: User) -> Event:
    """Get an event by ID."""
    event = check_not_found(event_config.get_event(event_id))
    if not event.is_visible_to(user):
        raise NotFound
    return event
