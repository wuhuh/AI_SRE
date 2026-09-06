"""Sensitive data masking helpers."""
from __future__ import annotations

import re

_SENSITIVE_KEY = re.compile(
    r"(?i)(api[_-]?key|password|passwd|secret|token|authorization)\s*[=:]\s*(?:(?:bearer)\s+)?([^\s,;]+)"
)


def mask_sensitive(value: str) -> str:
    return _SENSITIVE_KEY.sub(lambda m: f"{m.group(1)}={m.group(1)[:2]}***", value)
