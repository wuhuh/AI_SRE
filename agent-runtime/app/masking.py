"""Sensitive data masking helpers.

Applied to tool results and evidence before they are persisted or shipped to the
Control Plane. The masker targets the *value* of a sensitive key — never the key
name itself, which is what keeps a result still readable for debugging.
"""
from __future__ import annotations

import re

# key=value / key: value / key: Bearer value forms.
# group(1) = key name, group(2) = optional scheme (Bearer/Basic/Token), group(3) = secret value
_SENSITIVE_KEY = re.compile(
    r"(?i)(api[_-]?key|passwo?rd|secret|token|authorization)"
    r"\s*[=:]\s*"
    r"(?:(bearer|basic|token)\s+)?"
    r"([^\s,;\"']+)"
)

# Bare high-entropy tokens that look like credentials even without a key name
# (e.g. `sk-...` API keys, `ghp_...` PATs). Kept deliberately narrow so we do not
# blank out ordinary identifiers such as pod names or service names.
_BARE_SECRET = re.compile(r"\b(sk-[A-Za-z0-9_\-]{8,}|ghp_[A-Za-z0-9]{20,})\b")

MASK = "***"


def _mask_value(value: str) -> str:
    """Keep a short prefix (helps correlate *which* key it was) and mask the rest."""
    if len(value) <= 4:
        return MASK
    return value[:4] + MASK


def mask_sensitive(value: str) -> str:
    """Mask secret *values*, preserving the key name so results stay debuggable.

    >>> mask_sensitive("api_key=sk-1234567890")
    'api_key=sk-1***'
    """
    if not value:
        return value
    text = _SENSITIVE_KEY.sub(
        lambda m: f"{m.group(1)}={(m.group(2) + ' ') if m.group(2) else ''}{_mask_value(m.group(3))}",
        value,
    )
    return _BARE_SECRET.sub(lambda m: _mask_value(m.group(1)), text)


def mask_dict(data):
    """Recursively mask string leaves of a nested dict/list structure."""
    if isinstance(data, dict):
        return {k: mask_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [mask_dict(v) for v in data]
    if isinstance(data, str):
        return mask_sensitive(data)
    return data
