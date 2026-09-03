# Design Decisions

One line per decision made where the specification was ambiguous or silent.
Reviewed once at the end of the project.

## Environment / tooling

- **Python 3.11.15** used via `.venv` (spec asks 3.11+); system default is 3.10, an isolated venv avoids touching it.
- **Package layout**: `backend/` is the Python project root (`pyproject.toml` lives there); `core`, `services`, `api`, `models` are top-level importable packages, matching Section 4's `python -m core.cli`.

## Physics core

- (entries added as modules are built)
