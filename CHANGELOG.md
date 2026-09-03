# Changelog

All notable changes to this project. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versioning is date/phase based
until 1.0.

## [Unreleased]

## [1.0.0]

### Added

- **Physics core** (`backend/core/`, no web/DB deps): piecewise Saint-Robert burn
  rate with a self-consistent equilibrium-pressure solver; BATES / tubular /
  end-burner grains via a registry; real thrust-coefficient nozzle model with
  Summerfield separation and optional (off-by-default) throat erosion; quasi-steady
  time march with automatic `dt` convergence, ignition transient and exponential
  tail-off; NAR motor designation.
- **Analysis layer**: assembly layout / mass / CG / free volume / fit checks;
  thin & thick-wall (Lamé) structural FoS with a hard 2.0 gate; mandatory-liner
  thermal soak estimate; 1-DOF ISA flight; `differential_evolution` + Nelder-Mead
  mission solver that returns three candidates or names the binding constraint.
- **Export**: RASP `.eng` (≤ 32 pts, impulse within 1 %, ends at exactly 0),
  RockSim `.rse` (time-varying mass + CG), full-resolution CSV, versioned JSON
  design document, ReportLab PDF report (TR/EN), dimensioned SVG drawing,
  nozzle-contour CSV.
- **API** (FastAPI): anonymous design + simulate + export + mission; JWT auth
  (Argon2id, first user = admin); design save / share / fork; `/api/d/{slug}`;
  admin stats + runtime health; `ProcessPoolExecutor` + `job_id` polling so a
  mission solve never blocks forward simulations.
- **Frontend** (React + TS + Tailwind + Zustand + TanStack Query + Recharts):
  3-column designer, Basic/Expert modes, live simulation, contextual `?` tooltips
  on every parameter / metric / warning / derived measure, grain cross-section with
  a web slider, interactive scaled **engine cross-section** with editable dimensions
  and a BOM, quick altitude estimate panel with uncertainty bands, full TR/EN.
- **Deployment**: Docker Compose (`api`, `web`, `db`, `caddy`) with an optional
  `monitoring` profile (Prometheus + Grafana), Makefile, backup / cleanup scripts,
  GitHub Actions CI.
- **Docs**: `PHYSICS.md`, `VALIDATION.md`, `DEPLOYMENT.md`, generated
  `glossary_tr_en.md`.
