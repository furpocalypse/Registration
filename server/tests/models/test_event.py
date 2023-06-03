from datetime import date

from oes.registration.models.event import EventConfig


def test_load_event(example_events: EventConfig):
    event = example_events.get_event("example-event")
    assert event is not None
    assert event.id == "example-event"
    assert event.date == date(2024, 7, 4)
