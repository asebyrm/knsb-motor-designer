<p align="center">
  <img src="frontend/public/logo-original.png" alt="KNSB Motor Designer" width="120">
</p>

<h1 align="center">KNSB Motor Designer</h1>

<p align="center">
  Solid rocket motor design &amp; internal-ballistics simulation for amateur / university rocketry.<br>
  <em>by PARS Rocketry Team &mdash; <a href="https://github.com/asebyrm">github.com/asebyrm</a></em>
</p>

---

> ## ⚠️ Disclaimer
>
> This is an **engineering design tool, not a certification tool**. All simulation output is an
> estimate. A real motor must be verified by static fire testing. Solid propellant motors are
> subject to local law. Do not test without proper supervision and infrastructure.
> Exported files are marked **NOT FLIGHT CERTIFIED — amateur research motor, simulated data only**.
>
> This project contains **no information about propellant manufacture, mixing, casting, or igniter
> construction.** Its scope is geometry, internal ballistics, structural / thermal checks, and export.

---

## What it does

- **Forward design** — enter grain geometry and propellant parameters, get chamber pressure,
  thrust, total impulse and burn-time curves.
- **Inverse design (mission solver)** — describe a mission ("lift my 15 kg rocket to 500 m") and
  get three candidate motors with trade-offs and an uncertainty band.
- **Structural & thermal safety** — hoop-stress factor of safety for 3D-printed chambers, erosive
  burning check, liner thermal soak estimate. Unsafe designs are flagged and export is locked.
- **Export** — `.eng` (RASP), `.rse` (RockSim XML), CSV, JSON, dimensioned SVG drawing, PDF report.

Fuel: **KNSB** (potassium nitrate / sorbitol). Chambers: 3D-printed thermoplastics + Al-6061-T6
reference. Grains: BATES (multi-segment), tubular, end-burner.

## Quick start

```bash
cp .env.example .env          # edit secrets
docker compose up             # api + web + db + caddy
```

Then open `http://localhost` (or your domain). See `docs/DEPLOYMENT.md` for a from-scratch VPS setup.

### Physics core only (no web)

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python -m core.cli --example reference   # run the Section 13.1 reference case
pytest -q
```

## Extending

Adding a propellant = drop a YAML file in `backend/data/propellants/`.
Adding a chamber material = one YAML entry in `backend/data/materials/case_materials.yaml`.
Adding a grain geometry = subclass `GrainGeometry` and decorate with `@register_grain`.
No core engine code changes. See `CONTRIBUTING.md`.

## License

[AGPL-3.0-or-later](LICENSE). If you run a modified version as a network service, you must release
your changes under the same license.

## Credits

Internal-ballistics method follows Nakka and Sutton; RASP `.eng` format per thrustcurve.org.
Reference validation case from the İTÜ PARS internal-ballistics report (see `docs/PHYSICS.md`).
