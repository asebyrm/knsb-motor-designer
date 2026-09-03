"""Section 9.4 / acceptance 4b: every parameter, metric, warning code and derived
measure must have a string in BOTH tr.json and en.json. A missing key fails CI.

IDs come from the frontend registry (single source of truth) and from
``core.warnings.ALL_WARNING_CODES``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core.warnings import ALL_WARNING_CODES

_ROOT = Path(__file__).resolve().parents[2]
_REGISTRY = _ROOT / "frontend" / "src" / "lib" / "registry.ts"
_LOCALES = _ROOT / "locales"


def _load(locale: str) -> dict:
    with open(_LOCALES / f"{locale}.json", encoding="utf-8") as fh:
        return json.load(fh)


def _flatten(d: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys |= _flatten(v, key)
        else:
            keys.add(key)
    return keys


def _registry_ids() -> dict[str, list[str]]:
    text = _REGISTRY.read_text(encoding="utf-8")
    field_ids = re.findall(r'\bid:\s*"([a-z0-9_]+)"', text)
    metrics = re.findall(r'"([a-z_]+)"', re.search(r"METRICS = \[(.*?)\]", text, re.S).group(1))
    derived = re.findall(r'"([a-z_]+)"', re.search(r"DERIVED = \[(.*?)\]", text, re.S).group(1))
    actions = re.findall(r'"([a-z_]+)"', re.search(r"ACTIONS = \[(.*?)\]", text, re.S).group(1))
    return {
        "params": sorted(set(field_ids)),
        "metrics": sorted(set(metrics)),
        "derived": sorted(set(derived)),
        "actions": sorted(set(actions)),
    }


@pytest.fixture(scope="module")
def keys():
    return {"en": _flatten(_load("en")), "tr": _flatten(_load("tr"))}


@pytest.fixture(scope="module")
def ids():
    return _registry_ids()


@pytest.mark.parametrize("locale", ["en", "tr"])
def test_every_parameter_has_label_and_tooltip(keys, ids, locale):
    missing = []
    for pid in ids["params"]:
        if f"param.{pid}" not in keys[locale]:
            missing.append(f"param.{pid}")
        if f"info.param.{pid}" not in keys[locale]:
            missing.append(f"info.param.{pid}")
    assert not missing, f"{locale}: missing {missing}"


@pytest.mark.parametrize("locale", ["en", "tr"])
def test_every_metric_has_label_and_tooltip(keys, ids, locale):
    missing = [
        f"{ns}.{mid}"
        for mid in ids["metrics"]
        for ns in ("metric", "info.metric")
        if f"{ns}.{mid}" not in keys[locale]
    ]
    assert not missing, f"{locale}: missing {missing}"


@pytest.mark.parametrize("locale", ["en", "tr"])
def test_every_derived_measure_has_tooltip(keys, ids, locale):
    missing = [
        f"info.derived.{d}" for d in ids["derived"] if f"info.derived.{d}" not in keys[locale]
    ]
    assert not missing, f"{locale}: missing {missing}"


@pytest.mark.parametrize("locale", ["en", "tr"])
def test_every_action_has_tooltip(keys, ids, locale):
    missing = [
        f"info.action.{a}" for a in ids["actions"] if f"info.action.{a}" not in keys[locale]
    ]
    assert not missing, f"{locale}: missing {missing}"


@pytest.mark.parametrize("locale", ["en", "tr"])
def test_every_warning_code_has_a_message(keys, locale):
    missing = [
        f"info.warning.{c}" for c in ALL_WARNING_CODES if f"info.warning.{c}" not in keys[locale]
    ]
    assert not missing, f"{locale}: missing {missing}"


def test_tr_and_en_have_the_same_keys(keys):
    only_en = keys["en"] - keys["tr"]
    only_tr = keys["tr"] - keys["en"]
    assert not only_en and not only_tr, f"en-only={sorted(only_en)} tr-only={sorted(only_tr)}"
