"""Identifier validation."""
import re

PATTERN = re.compile(r"^(?![0-9-])[a-zA-Z0-9-_]+(?<!-)$")


def validate_identifier(a, i, v):
    """Attrs validator for an identifier."""
    if not isinstance(v, str):
        raise TypeError(f"Invalid identifier: {v}")
    if not PATTERN.match(v):
        raise ValueError(f"Invalid identifier: {v}")
