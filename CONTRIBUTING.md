# Contributing

Thanks for helping improve KNSB Motor Designer. This project is AGPL-3.0 — by
contributing you agree your work is licensed the same way.

## Ground rules

- **The `core/` package has no web/DB imports.** Pure functions + dataclasses, SI units
  everywhere, every physics function's docstring states its equation and units.
- User-facing text never lives in code. Add a key to `locales/en.json` **and**
  `locales/tr.json` (the coverage test fails otherwise) and read it with `t(...)` /
  `core.i18n.t(...)`.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`). Green CI
  (`ruff` + `pytest`, `tsc -b` + `oxlint` + `vite build`) is required to merge.

## Dev setup

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install -e "./backend[api,dev]"
cd frontend && npm ci && cd ..

make api    # http://localhost:8000  (docs at /docs)
make web    # http://localhost:5173
make test   # backend suite
```

## Adding a propellant — YAML only, no code change

Drop `backend/data/propellants/<id>.yaml`:

```yaml
id: kndx
name_tr: "KNDX (…)"
name_en: "KNDX (…)"
composition: "KNO3 65% / Dextrose 35%"
density_ideal: 1879
density_factor: 0.95
c_star_ideal: 912.0
c_star_efficiency: 0.95
gamma: 1.1308
flame_temperature: 1710
molar_mass: 42.39
burn_rate_ranges:                 # r_b = a·(p_c[MPa])^n  → mm/s
  - {p_min: 0.10, p_max: 0.78, a: 8.875, n: 0.619}
  - {p_min: 0.78, p_max: 2.57, a: 7.553, n: -0.009}
  # …
```

It shows up in the catalogue and the UI dropdown immediately. `test_extensibility.py`
proves a new YAML needs no core edits.

## Adding a case or liner material — one YAML entry

`backend/data/materials/case_materials.yaml` (or `liner_materials.yaml`). Include the
tensile strength, `print_direction_factor`, thermal properties and a `notes_key`; then
add `material.<id>.notes` / `liner.<id>.notes` to both locale files.

## Adding a grain geometry — subclass + decorator

```python
from core.grains.base import GrainGeometry, register_grain

@register_grain("finocyl")
class FinocylGrain(GrainGeometry):
    def burn_area(self, web): ...
    def volume(self, web): ...
    def port_area(self, web): ...
    def web_thickness(self): ...
    def outer_diameter(self): ...
    def envelope_length(self): ...
    def cross_section_svg(self, web): ...
    def validate(self): ...
```

No engine, service or API file changes — the registry and `services/design_service.py`
pick it up by key. Add a `param.*` + `info.param.*` pair for any new fields.

## Tests

Put physics tests next to the module they cover in `backend/tests/`. Mark anything
that takes seconds (`@pytest.mark.slow`). The Section 13.1 regression
(`test_reference_case.py`) must stay green and its expected over-pressure must **not**
be "fixed".
