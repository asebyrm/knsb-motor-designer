# Progress Log

Recovery point for a resumed session. Updated every commit.
To resume: `git log --oneline -20`, `git status`, then
`cd backend && ../.venv/bin/python -m pytest -q -m "not slow"` before trusting this file.

## Current phase

Phases 1-6 **COMPLETE**. 131 backend tests green (128 fast + 3 slow), ruff clean,
`frontend` builds (`tsc -b && vite build`), oxlint clean. Starting Phase 8
(Docker, Caddy, docs, CI, README, GitHub publish). Phase 7 admin panel done inline.

## Phases 1-4 (backend) — done

core physics + analysis + export + FastAPI. Tags v0.1-core .. v0.4-api.
Run API: `cd backend && ENVIRONMENT=development ../.venv/bin/uvicorn api.main:app --reload`

## Phase 5-6 (frontend) — done

- Vite + React 18 + TS + Tailwind(3) + Zustand + TanStack Query + react-i18next + Recharts.
- `frontend/src/`: `i18n.ts`, `api.ts`, `store.ts`, `types.ts`,
  `lib/{registry,units,examples}.ts`,
  `components/{ui,ParamPanel,Charts,GrainCrossSection,EngineCrossSection,ResultsPanel,
  MissionPanel,Topbar,Logo,AuthDialog,ExportDialog}.tsx`,
  `pages/{Designer,Admin}.tsx`, `App.tsx`, `main.tsx`.
- 3-column layout, Basic/Expert, unit + theme + TR/EN toggles, examples menu,
  first-run disclaimer, contextual `?` tooltips (hover 400 ms / focus / tap),
  grain cross-section + web slider, Section 10.1 engine cross-section (scaled SVG,
  dimension lines + editable dimension table, derived italic, red on bad fit,
  SVG + BOM CSV download), mission panel (job poll, 3 candidates, ±band, scope note,
  infeasible → binding constraint + apply-suggestion), export dialog (423 lock + accept-risk).
- `backend/api/routes/tools.py` (neutral-length, optimum-expansion helpers).
- `locales/{en,tr}.json` canonical; `scripts/gen_glossary.py` → `docs/glossary_tr_en.md`.
- `tests/test_i18n_coverage.py` (11): every param/metric/derived/action/warning has tr+en,
  key sets identical (acceptance 4b, 7).

## Next step

Phase 8:
- `docker-compose.yml` (api, web/nginx, db postgres:16, caddy) + `monitoring` profile
  (prometheus + grafana, default off).
- `backend/Dockerfile`, `frontend/Dockerfile`, `Caddyfile`, `Makefile`.
- `docs/DEPLOYMENT.md`, `docs/VALIDATION.md` (openMotor + Nakka compare), `docs/PHYSICS.md`.
- `README.md` (already drafted) + `README.tr.md`, `CONTRIBUTING.md`, `CHANGELOG.md`,
  `.github/workflows/ci.yml`.
- `scripts/{cleanup_exports.sh,backup_db.sh}`.
- GitHub publish per Section 12.1 (needs `gh auth login` by the user; secret-scan first).

## Last files touched

- entire `frontend/`, `locales/*.json`, `backend/api/routes/tools.py`,
  `backend/tests/test_i18n_coverage.py`, `scripts/gen_glossary.py`, `docs/glossary_tr_en.md`
