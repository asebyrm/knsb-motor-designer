<p align="center">
  <img src="frontend/public/favicon.svg" alt="" width="72">
</p>

<h1 align="center">KNSB Motor Designer</h1>

<p align="center">
  Solid rocket motor design &amp; internal-ballistics simulation for amateur / university rocketry.<br>
  <em>by <a href="https://github.com/asebyrm">PARS Rocketry Team</a></em> ·
  <a href="README.tr.md">Türkçe</a>
</p>

---

> ## ⚠️ Disclaimer
>
> This is an **engineering design tool, not a certification tool.** All simulation output
> is an estimate; a real motor must be verified by static fire testing. Solid propellant
> motors are subject to local law — do not test without proper supervision and infrastructure.
> Every export is marked **NOT FLIGHT CERTIFIED — amateur research motor, simulated data only.**
>
> This project contains **no information about propellant manufacture, mixing, casting or
> igniters.** Its scope is geometry, internal ballistics, structural / thermal checks and export.

---

## What it does

- **Forward design** — enter grain geometry and propellant parameters, get chamber pressure,
  thrust, `Kn`, mass-flow, total-impulse and burn-time curves, with the burning grain animated
  by a web slider.
- **Quick altitude estimate (inverse design)** — enter rocket mass, body diameter and a target
  apogee; a 1-DOF solver proposes **three** motors (lightest / lowest peak pressure / closest to
  target), each with an uncertainty band. An infeasible mission never returns empty — it names
  the binding constraint and a one-click numeric fix.
- **Safety first** — hoop-stress factor of safety for 3D-printed chambers (FDM vs SLS knock-down),
  thick-wall Lamé model when needed, mandatory ablative liner with a thermal-soak estimate,
  erosive-burning (`J`) and `L*` checks. A design with `FoS < 2` is flagged **UNSAFE** and
  `.eng` / `.rse` export is locked until you explicitly accept the risk.
- **Interactive engine cross-section** — a scaled, dimensioned longitudinal drawing; input
  dimensions are click-to-edit and re-run the simulation, derived dimensions are shown
  distinctly, geometry that doesn't fit turns red. Download it as SVG; the parts list (BOM)
  total mass matches the `.eng` header exactly.
- **Export** — `.eng` (RASP), `.rse` (RockSim XML with time-varying mass + CG), CSV, JSON,
  PDF report, dimensioned SVG, nozzle-contour CSV.
- **Accounts (optional)** — everything works anonymously (design saved in `localStorage`).
  Log in only to save, share (`/d/{slug}`) and fork designs. Admin panel shows usage stats
  and runtime health.
- **Bilingual** — full Turkish and English; contextual `?` help on every field, result and
  warning.

Fuel: **KNSB** (potassium nitrate / sorbitol), fine and granular oxidizer variants; KNDX
ships as a drop-in YAML. Chambers: PLA, PETG, ABS, PA12, PA6-CF, PC + Al-6061-T6 reference.
Grains: BATES (multi-segment), tubular, end-burner.

## Quick start (Docker)

```bash
git clone https://github.com/asebyrm/knsb-motor-designer && cd knsb-motor-designer
cp .env.example .env
python3 -c "import secrets;print('SECRET_KEY='+secrets.token_urlsafe(48))" >> .env
# edit .env: DOMAIN, ACME_EMAIL, POSTGRES_PASSWORD
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Open `https://<your-domain>`. First registered account becomes admin. Full walkthrough:
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

### Physics core / API only (no Docker)

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install -e "./backend[api,dev]"

cd backend
python -m core.cli example reference     # Section 13.1 regression case
python -m core.cli mission --dry-mass 6 --diameter 0.10 --apogee 900
pytest -q                                # 130+ tests
../.venv/bin/uvicorn api.main:app --reload   # http://localhost:8000/docs

cd ../frontend && npm ci && npm run dev   # http://localhost:5173
```

## Extending

| To add… | Do… | Core code change |
| --- | --- | --- |
| a propellant | drop a YAML in `backend/data/propellants/` | none |
| a chamber / liner material | one entry in `backend/data/materials/*.yaml` | none |
| a grain geometry | subclass `GrainGeometry`, add `@register_grain("key")` | none |

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Documentation

- [`docs/PHYSICS.md`](docs/PHYSICS.md) — every equation, units and sources (Nakka, Sutton, RASP).
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — reference case, openMotor and Nakka comparisons.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — from a bare VPS to HTTPS.
- [`docs/glossary_tr_en.md`](docs/glossary_tr_en.md) — generated TR/EN term glossary.

## License

[AGPL-3.0-or-later](LICENSE). Running a modified version as a network service obliges you to
publish your changes under the same license.

## Credits

Internal-ballistics method follows **Richard Nakka** and **Sutton, *Rocket Propulsion
Elements***; the RASP `.eng` format per thrustcurve.org. The Section 13.1 regression case is
from the **İTÜ PARS Rocket Team** internal-ballistics report.
