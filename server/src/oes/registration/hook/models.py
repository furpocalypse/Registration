"""Hook models."""
from __future__ import annotations

from collections.abc import Generator, Mapping, Sequence
from enum import Enum
from typing import Any, Union

from attrs import Factory, field, frozen
from oes.hook import (
    ExecutableHookConfig,
    Hook,
    HttpHookConfig,
    PythonHookConfig,
    executable_hook_factory,
    http_hook_factory,
    python_hook_factory,
)
from oes.registration.http_client import get_http_client
from oes.registration.serialization.json import json_dumps
from typing_extensions import assert_never

RETRY_SECONDS = (
    5,
    30,
    60,
    600,
    3600,
    7200,
    43200,
    86400,
)
"""How many seconds between each retry."""

NUM_RETRIES = len(RETRY_SECONDS)
"""Number of attempts to re-send a hook."""


class HookEvent(str, Enum):
    """Hook event types."""

    email_auth_code = "email.auth_code"
    """An email auth code is generated."""

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


async def _http_func(body: Any, config: HttpHookConfig) -> Any:
    client = get_http_client()
    json_data = json_dumps(body)
    response = await client.post(
        config.url,
        content=json_data,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    if response.status_code == 204:
        return None
    else:
        return response.json()


@frozen
class HookConfigEntry:
    """Hook configuration entry."""

    on: HookEvent
    """The hook trigger."""

    hook: HookConfigObject
    """The hook configuration."""

    retry: bool = True
    """Whether to retry the hook if it fails."""

    def get_hook(self) -> Hook:
        """Get the configured :class:`Hook`."""
        if isinstance(self.hook, URLOnlyHTTPHookConfig):
            return http_hook_factory(
                HttpHookConfig(
                    self.hook.url,
                    _http_func,
                )
            )
        elif isinstance(self.hook, ExecutableHookConfig):
            return executable_hook_factory(self.hook)
        elif isinstance(self.hook, PythonHookConfig):
            return python_hook_factory(self.hook)
        else:
            assert_never(self.hook)


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
