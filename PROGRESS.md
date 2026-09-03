# Progress Log

Recovery point for a resumed session.
To resume: `git log --oneline -20`, `git status`, then
`cd backend && ../.venv/bin/python -m pytest -q -m "not slow"`.

## Status: v1.0 — all 8 phases complete

Tags: v0.1-core, v0.2-analysis, v0.3-export, v0.4-api, v0.5-ui, v0.6-ai, v1.0.
- 123 backend tests green (120 fast + 3 @slow: mission solver ×2, concurrency ×1).
- `ruff check .` clean; frontend `tsc -b` + `oxlint` clean; `vite build` OK.
- `docker compose config` valid (needs SECRET_KEY + POSTGRES_PASSWORD in env).

## What exists

- `backend/core/` — pure physics (units, warnings, propellant, grains, nozzle,
  sampling, ballistics, assembly, structure, thermal, flight, solver, examples, cli,
  branding, i18n, export/*).
- `backend/services/` — design / simulation / export / mission / auth / infra /
  executors.
- `backend/api/` — FastAPI app + routes (health+catalog, auth, designs, simulate,
  mission+jobs, export, admin, tools). `backend/models/` + `backend/alembic/`.
- `frontend/` — Vite React TS app (see src/{components,pages,lib}).
- `locales/{en,tr}.json` (canonical, shared) + `scripts/gen_glossary.py`.
- Docker: `backend/Dockerfile`, `frontend/Dockerfile`+`nginx.conf`, `docker-compose.yml`
  (+ `monitoring` profile), `Caddyfile`, `Makefile`, `monitoring/`.
- Docs: `docs/{PHYSICS,VALIDATION,DEPLOYMENT,glossary_tr_en}.md`, `README.md`,
  `README.tr.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `DECISIONS.md`.
- `.github/workflows/ci.yml`, `scripts/{cleanup_exports,backup_db}.sh`.

## Remaining (needs the user)

1. **GitHub publish** — `gh` is not installed on this machine. After
   `brew install gh && gh auth login`:
   ```
   gh repo create asebyrm/knsb-motor-designer --public --source=. --remote=origin --push
   ```
   Secret scan already run: no keys/passwords/tokens in tree or history
   (`.env` absent, only `.env.example`).
2. **OpenRocket load screenshot** — export the `mid` example as `.eng`, load it in
   OpenRocket, save `docs/img/openrocket-load.png` (acceptance 3). Format is
   spec-compliant and round-trips through the in-repo parser.
3. **openMotor comparison numbers** — `docs/VALIDATION.md` has the table with this
   engine's values and expected bands; fill the openMotor column from a local run.
