# Progress Log

Recovery point for a resumed session. Updated every commit.
To resume: run `git log --oneline -20`, `git status`, then `cd backend && ../.venv/bin/python -m pytest -q`
before trusting this file.

## Current phase

Phase 1 — Physics core: **COMPLETE**. Starting Phase 2 (analysis layer).

## Modules done

- Scaffold, `.gitignore`, `pyproject.toml`, AGPL-3.0 `LICENSE`, `DECISIONS.md`.
- `.venv` Python 3.11.15.
- `core/units.py` — SI constants + I/O conversions.
- `core/warnings.py` — coded diagnostics, `ALL_WARNING_CODES` catalogue (46 codes).
- `core/propellant.py` — piecewise Saint-Robert, self-consistent equilibrium solver + Brent fallback.
- `core/grains/` — `base` (ABC + registry), `bates` (+ neutral-length solver), `tubular`, `endburner`.
- `core/nozzle.py` — real Cf, area-Mach exit solve, Summerfield separation, throat erosion (off by default).
- `core/sampling.py` — shape-preserving RDP downsample (used for 500-pt API + 32-pt .eng).
- `core/ballistics.py` — quasi-steady time march, dt convergence, ignition transient, tail-off,
  MEOP on erosionless curve, NAR designation.
- `core/examples.py` — reference case + 3 sample motors.
- `core/cli.py` — `python -m core.cli example reference | simulate ...`.
- `data/propellants/knsb.yaml`.

## Tests passing (54)

- `test_propellant.py` (12) — unit-conversion trap, negative-n band solver.
- `test_grains.py` (9) — BATES neutrality < 2%, volume/area identity.
- `test_nozzle.py` (9) — Cf, eps solve, separation, erosion.
- `test_ballistics.py` (12) — mass conservation, dt convergence, downsample impulse < 1%, NAR.
- `test_reference_case.py` (10) — **Section 13.1: peak 21.99 bar, WARN_MEOP_EXCEEDED fires.**

## Next step

Phase 2: `core/assembly.py` (compute_layout, total_length/mass, CG, free_volume, validate_fit),
then `structure.py`, `thermal.py`, `flight.py`, `solver.py`, and `data/materials/case_materials.yaml`
+ `data/liners/`.

## Last files touched

- all of `backend/core/`, `backend/tests/`, `backend/data/propellants/knsb.yaml`
