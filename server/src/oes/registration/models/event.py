"""Event models."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date  # noqa
from typing import TYPE_CHECKING, Any, Optional

from attrs import Factory, field, frozen
from oes.registration.models.identifier import validate_identifier
from oes.template import Condition, Template, evaluate
from typing_extensions import Self

if TYPE_CHECKING:
    from oes.registration.auth.user import User


class Whenable(ABC):
    """Class with a ``when`` condition."""

    @property
    @abstractmethod
    def when(self) -> Condition:
        """The ``when`` condition."""
        ...

    def when_matches(self, **context: Any) -> bool:
        """Return whether the conditions match."""
        return bool(evaluate(self.when, context))


@frozen(kw_only=True)
class RegistrationOption:
    """A registration option."""

    id: str = field(validator=validate_identifier)
    """The option ID."""

    name: str
    """The option name."""

    description: Optional[str] = None
    """The option description."""


@frozen(kw_only=True)
class ModifierRule(Whenable):
    """Event line item modifier rule."""

    type_id: Optional[Template] = None
    """A type ID for the modifier."""

    name: Template
    """The modifier name."""

    amount: int
    """The amount."""

    when: Condition
    """The condition/conditions when the modifier applies."""


@frozen(kw_only=True)
class LineItemRule(Whenable):
    """Event line item pricing rule."""

    type_id: Optional[str] = None
    """A type ID for the line item."""

    name: Template
    """The line item name."""

    description: Optional[Template] = None
    """The line item description."""

    price: int
    """The price."""

    modifiers: Sequence[ModifierRule] = ()
    """Modifier rules."""

    when: Condition
    """The condition/conditions when the line item is present."""


@frozen
class RegistrationDisplayOptions:
    """Display options for a registration in the self-service view."""

    title: Template = Template("{{registration.display_name}}")
    subtitle: Template = Template("")
    description: Template = Template("")


@frozen
class EventDisplayOptions:
    """Display options."""

    registration: RegistrationDisplayOptions = RegistrationDisplayOptions()
    """The template for how to display a registration in the self-service view."""


@frozen
class EventInterviewOption(Whenable):
    """An available event interview."""

    id: str
    """The interview ID."""

    name: str
    """The interview name."""

    when: Condition = ()
    """The condition."""


@frozen(kw_only=True)
class Event:
    """Event class."""

    id: str = field(validator=validate_identifier)
    """The event ID."""

    name: str
    """The event name."""

    description: Optional[str] = None
    """The event description."""

    date: date
    """The event start date."""

    open: bool = False
    """Whether the event is open."""

    visible: bool = False
    """Whether the event is visible."""

    registration_options: Sequence[RegistrationOption] = ()
    """The registration options."""

    add_interviews: Sequence[EventInterviewOption] = ()
    """The interviews available for adding a new registration."""

    change_interviews: Sequence[EventInterviewOption] = ()
    """The interviews available for changing an existing registration."""

    pricing_rules: Sequence[LineItemRule] = ()
    """Line item pricing rules."""

    display_options: EventDisplayOptions = EventDisplayOptions()
    """Display options."""

    def is_visible_to(self, user: User) -> bool:
        """Get whether the event is visible to the given user."""
        return self.visible or user.is_admin

    def is_open_to(self, user: User) -> bool:
        """Get whether the event is open to the given user."""
        return self.open and self.is_visible_to(user) or user.is_admin


@frozen(kw_only=True)
class SimpleEventInfo:
    """A subset of event information sent to things like pricing hooks."""

    id: str
    name: str
    description: Optional[str] = None
    date: date
    open: bool = False
    visible: bool = False
    registration_options: Sequence[RegistrationOption] = ()

    @classmethod
    def create(cls, event: Event) -> Self:
        """Create from a :class:`Event`."""
        return cls(
            id=event.id,
            name=event.name,
            description=event.description,
            date=event.date,
            open=event.open,
            visible=event.visible,
            registration_options=tuple(event.registration_options),
        )


@frozen
class EventConfig:
    """Event configuration."""

    events: Sequence[Event]

    _events_by_id: dict[str, Event] = field(
        init=False,
        eq=False,
        default=Factory(lambda s: {e.id: e for e in s.events}, takes_self=True),
    )

    def get_event(self, id: str) -> Optional[Event]:
        """Get an event by ID."""
        return self._events_by_id.get(id)
