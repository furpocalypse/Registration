"""Config module."""
from collections.abc import Sequence
from pathlib import Path

from attr import frozen
from oes.registration.models.config import Config
from oes.registration.models.event import Event, EventConfig
from oes.registration.serialization import get_config_converter
from ruamel.yaml import YAML

yaml = YAML(typ="safe")


@frozen
class CommandLineConfig:
    """Command line config settings."""

    port: int
    bind: str
    root_path: str
    debug: bool
    reload: bool
    insecure: bool
    no_auth: bool
    config: Path
    events: Path


def load_config(path: Path) -> Config:
    """Load the main configuration."""
    doc = yaml.load(path)
    config = get_config_converter().structure(doc, Config)
    return config


def load_event_config(path: Path) -> EventConfig:
    """Load the event config."""
    doc = yaml.load(path)
    events = get_config_converter().structure(doc, Sequence[Event])
    return EventConfig(events)
