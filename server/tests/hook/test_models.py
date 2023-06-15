import pytest
from oes.hook import PythonHookConfig
from oes.registration.hook.models import (
    HookConfig,
    HookConfigEntry,
    HookEvent,
    URLOnlyHTTPHookConfig,
)
from oes.registration.serialization import get_config_converter
from ruamel.yaml import YAML

config_str = """
hooks:
  - on: registration.created
    hook:
      python: tests.hook.test_models:hook_fn
  - on: cart.price
    hook:
      url: http://localhost:8000/test
"""

yaml = YAML(typ="safe")


def hook_fn(obj):
    pass


def hook_fn2(obj):
    pass


@pytest.fixture
def hook_config():
    doc = yaml.load(config_str)
    return get_config_converter().structure(doc, HookConfig)


def test_build_hook_config(hook_config: HookConfig):
    expected = HookConfig(
        [
            HookConfigEntry(
                on=HookEvent.registration_created,
                hook=PythonHookConfig(
                    python="tests.hook.test_models:hook_fn",
                ),
            ),
            HookConfigEntry(
                on=HookEvent.cart_price,
                hook=URLOnlyHTTPHookConfig(
                    url="http://localhost:8000/test",
                ),
            ),
        ]
    )

    assert list(hook_config) == list(expected.hooks)
    assert hook_config == expected


def test_get_hooks_by_event(hook_config: HookConfig):
    assert list(hook_config.get_by_event(HookEvent.cart_price)) == [
        HookConfigEntry(
            on=HookEvent.cart_price,
            hook=URLOnlyHTTPHookConfig(
                url="http://localhost:8000/test",
            ),
        )
    ]


def test_hook_config_exists(hook_config: HookConfig):
    good = PythonHookConfig(
        python="tests.hook.test_models:hook_fn",
    )

    bad = PythonHookConfig(
        python="tests.hook.test_models:hook_fn2",
    )

    assert hook_config.hook_config_exists(HookEvent.registration_created, good)
    assert not hook_config.hook_config_exists(HookEvent.registration_created, bad)
