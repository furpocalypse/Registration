"""Hook models."""
from collections.abc import Generator, Mapping, Sequence
from enum import Enum
from typing import Union

from attrs import Factory, field, frozen
from oes.hook import ExecutableHookConfig, PythonHookConfig


class HookEvent(str, Enum):
    """Hook event types."""

    registration_created = "registration.created"
    """A registration is created or transitions to the ``created`` state."""

    registration_updated = "registration.updated"
    """A registration is updated."""

    registration_canceled = "registration.canceled"
    """A registration is canceled."""

    cart_price = "cart.price"
    """A cart is being priced."""

    checkout_created = "checkout.created"
    """A checkout is created."""

    checkout_closed = "checkout.completed"
    """A checkout is completed."""

    checkout_canceled = "checkout.canceled"
    """A checkout is canceled."""


@frozen
class URLOnlyHTTPHookConfig:
    """Config for a webhook without needing to set ``http_func``."""

    url: str = field(repr=False)
    """The URL."""


HookConfigObject = Union[
    URLOnlyHTTPHookConfig,
    ExecutableHookConfig,
    PythonHookConfig,
]
"""Hook configuration types."""


@frozen
class HookConfigEntry:
    """Hook configuration entry."""

    on: HookEvent
    """The hook trigger."""

    hook: HookConfigObject
    """The hook configuration."""

    retry: bool = True
    """Whether to retry the hook if it fails."""


@frozen
class HookConfig:
    """Hook configuration."""

    def _build_by_event(self) -> dict[str, list[HookConfigEntry]]:
        dict_: dict[str, list[HookConfigEntry]] = {}
        for obj in self.hooks:
            list_ = dict_.setdefault(obj.on, [])
            list_.append(obj)
        return dict_

    hooks: Sequence[HookConfigEntry] = field(converter=lambda v: tuple(v))
    _by_event: Mapping[str, list[HookConfigEntry]] = field(
        init=False,
        eq=False,
        default=Factory(_build_by_event, takes_self=True),
    )

    def __iter__(self) -> Generator[HookConfigEntry, None, None]:
        yield from self.hooks

    def get_by_event(
        self, hook_event: HookEvent
    ) -> Generator[HookConfigEntry, None, None]:
        """Yield :class:`HookConfigEntry` objects for the given event type."""
        yield from self._by_event.get(hook_event, [])

    def hook_config_exists(self, hook_event: HookEvent, config: object) -> bool:
        """Get whether the given hook config exists in this configuration.

        Used e.g. to check if an executable hook loaded from the database actually
        corresponds to an entry in the config file.

        Args:
            hook_event: The event type.
            config: The configuration object.
        """
        for entry in self._by_event.get(hook_event, []):
            if entry.hook == config:
                return True
        else:
            return False
