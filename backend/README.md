# backend

Python backend for KNSB Motor Designer.

- `core/` — pure physics, no web/DB dependency. Run `python -m core.cli`.
- `services/` — application logic shared by every interface.
- `api/` — FastAPI routers (thin).
- `models/` — SQLAlchemy models.

See the repository root `README.md` for the full picture.
