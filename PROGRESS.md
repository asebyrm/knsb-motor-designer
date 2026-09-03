# Progress Log

Recovery point for a resumed session. Updated every commit.
To resume: `git log --oneline -20`, `git status`, then
`cd backend && ../.venv/bin/python -m pytest -q -m "not slow"` before trusting this file.

## Current phase

Phases 1-3 **COMPLETE** (tags v0.1-core, v0.2-analysis, v0.3-export).
Starting Phase 4 (FastAPI + DB + auth + admin + ProcessPool/job polling).

## Phase 1 — physics core (done)

- `core/units.py`, `core/warnings.py` (46-code catalogue), `core/propellant.py`
  (piecewise Saint-Robert + self-consistent equilibrium solver / Brent fallback).
- `core/grains/` — `base` (ABC + `@register_grain`), `bates` (+ neutral-length solver),
  `tubular`, `endburner`.
- `core/nozzle.py` — real Cf via area-Mach solve, Summerfield separation, optional erosion.
- `core/sampling.py` — RDP shape-preserving downsample (500-pt API / 32-pt .eng).
- `core/ballistics.py` — quasi-steady march, dt-convergence, ignition transient, tail-off,
  MEOP on the erosionless curve, NAR designation.
- `core/examples.py`, `core/cli.py`, `data/propellants/knsb.yaml`.

## Phase 2 — analysis layer (done)

- `core/materials.py` + `data/materials/case_materials.yaml` (7) + `liner_materials.yaml` (5).
- `core/assembly.py` — compute_layout, total_length/mass, CG(web), free_volume(web),
  characteristic_length, validate_fit, bill_of_materials (+ `bom_total_mass`).
- `core/structure.py` — thin/thick-wall hoop stress + Von Mises, FoS gate (min 2.0),
  print-method knock-down, shear-bolt sizing.
- `core/thermal.py` — mandatory liner, semi-infinite soak, ablation burn-through.
- `core/flight.py` — ISA atmosphere, 1-DOF RK4, rail-exit / apogee / max-g.
- `core/solver.py` — mission solver (`solve_mission`, ProcessPool-safe), 3-candidate output,
  constraint-relaxation suggestion. `core/cli.py mission` subcommand.

## Tests passing (82 = 80 fast + 2 @slow)

- P1: test_propellant 12, test_grains 9, test_nozzle 9, test_ballistics 12,
  test_reference_case 10 (**13.1: peak 21.99 bar, WARN_MEOP_EXCEEDED**).
- P2: test_assembly 9, test_structure 5, test_thermal 5, test_flight 8,
  test_solver 2 @slow (**13.2 infeasible mission → binding constraint + numeric fix**).

## Phase 3 — export (done)

- `core/export/{eng,rse,tabular,drawing,report}.py`, `core/branding.py`, `core/i18n.py`.
- `services/{design,simulation,export}_service.py`. `mission_service.py` still TODO (Phase 4,
  wraps `core.solver.solve_mission` in a ProcessPool + job store).
- `data/propellants/kndx.yaml`.
- Tests: test_export (11), test_services (4), test_extensibility (3). 99 total (97 fast + 2 slow).

## Next step

Phase 4 — `backend/api/` FastAPI app, `backend/models/` SQLAlchemy + Alembic, JWT auth
(Argon2id), admin endpoints, OpenAPI. `services/mission_service.py` +
`services/infra.py` (RateLimiter, JobStore abstract + in-memory impls) +
`ProcessPoolExecutor` wiring per Section 12.2. `tests/load/` concurrency test.
Config via pydantic-settings reading os.environ (fail loudly if secrets missing).

## Last files touched

- `backend/core/export/*`, `backend/core/{branding,i18n}.py`
- `backend/services/{design,simulation,export}_service.py`
- `backend/data/propellants/kndx.yaml`
- `backend/tests/test_{export,services,extensibility}.py`
