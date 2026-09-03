#!/usr/bin/env python3
"""Generate docs/glossary_tr_en.md from the canonical locale files.

Section 9.4 / 11: the glossary is produced, never hand-written, so the two
descriptions never diverge. Run from the repo root:  python scripts/gen_glossary.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "locales"
OUT = ROOT / "docs" / "glossary_tr_en.md"

SECTIONS = [
    ("Parameters", "param", "info.param"),
    ("Result metrics", "metric", "info.metric"),
    ("Derived measures", None, "info.derived"),
    ("Warnings — what to do", None, "info.warning"),
    ("Action buttons", "action", "info.action"),
]


def load(locale: str) -> dict:
    return json.loads((LOCALES / f"{locale}.json").read_text(encoding="utf-8"))


def get(d: dict, dotted: str) -> str | None:
    node: object = d
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


def main() -> None:
    en, tr = load("en"), load("tr")
    lines = [
        "# Glossary (TR / EN)",
        "",
        "> Generated from `locales/{en,tr}.json` by `scripts/gen_glossary.py`. Do not edit by hand.",
        "",
    ]
    for title, label_ns, tip_ns in SECTIONS:
        lines.append(f"## {title}\n")
        lines.append("| Key | EN | TR |")
        lines.append("| --- | --- | --- |")
        # collect ids present under the tooltip namespace
        node = en
        for part in tip_ns.split("."):
            node = node.get(part, {})
        for key in sorted(node):
            en_label = get(en, f"{label_ns}.{key}") if label_ns else key
            tr_label = get(tr, f"{label_ns}.{key}") if label_ns else key
            en_tip = get(en, f"{tip_ns}.{key}") or ""
            tr_tip = get(tr, f"{tip_ns}.{key}") or ""
            name = en_label if en_label == tr_label or not label_ns else f"{en_label} / {tr_label}"
            lines.append(f"| `{key}` — {name} | {en_tip} | {tr_tip} |")
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
