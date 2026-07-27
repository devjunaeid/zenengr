"""Slug validation utility.

Regex: ^[a-z0-9]+(-[a-z0-9]+)*$
Permits lowercase alphanumeric segments separated by single hyphens.
No leading/trailing/double hyphens.
"""

from __future__ import annotations

import re

SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_slug(value: str) -> bool:
    """Return True if value is a valid tenant slug."""
    return bool(SLUG_REGEX.match(value))
