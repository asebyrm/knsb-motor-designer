"""Minimal translation lookup shared by the PDF report and any server-side text.

The canonical locale files live in ``<repo>/locales/{tr,en}.json`` (same files the
frontend bundles, Section 11). Override the directory with ``LOCALES_DIR``.

The core still never *returns* localised text to API clients - it returns warning
codes. This helper exists only for artefacts the backend renders directly (PDF).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "locales"
SUPPORTED = ("tr", "en")


def locales_dir() -> Path:
    return Path(os.environ.get("LOCALES_DIR", str(_DEFAULT_DIR)))


@lru_cache(maxsize=8)
def _load(locale: str) -> dict:
    path = locales_dir() / f"{locale}.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _flatten(d: dict, prefix: str = "") -> dict:
    out: dict[str, str] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


@lru_cache(maxsize=8)
def _flat(locale: str) -> dict:
    return _flatten(_load(locale))


def t(key: str, locale: str = "en", /, **params) -> str:
    """Translate ``key`` for ``locale``; falls back to English then to the key itself.

    ``{name}`` placeholders in the string are filled from ``params``.
    """
    locale = locale if locale in SUPPORTED else "en"
    value = _flat(locale).get(key) or _flat("en").get(key) or key
    if params:
        try:
            return value.format(**params)
        except (KeyError, IndexError, ValueError):
            return value
    return value


def available_keys(locale: str = "en") -> set[str]:
    return set(_flat(locale).keys())
