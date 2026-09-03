# Progress Log

Recovery point for a resumed session. Updated every commit.
To resume: `git log --oneline -20`, `git status`, then
`cd backend && ../.venv/bin/python -m pytest -q -m "not slow"` before trusting this file.

## Current phase

Phases 1 & 2 **COMPLETE**. Starting Phase 3 (export: .eng, .rse, CSV, JSON, PDF).

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

## Next step

Phase 3 — export writers (`core/export/` or `services/export_service.py`):
`.eng` (RASP, ≤32 pts, impulse within 1%, ends at 0), `.rse` (RockSim XML, time-varying
mass+CG), CSV (full-res), JSON (versioned design schema), PDF (ReportLab). Round-trip +
downsampling tests. Then `services/{design,simulation,mission}_service.py`.

## Last files touched

- `backend/core/{materials,assembly,structure,thermal,flight,solver,cli}.py`
- `backend/data/materials/*.yaml`
- `backend/tests/test_{assembly,structure,thermal,flight,solver}.py`
