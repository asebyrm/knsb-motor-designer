# Deployment

From a clean Ubuntu 22.04/24.04 VPS to a running, TLS-terminated instance.

## 0. Prerequisites

- A domain (e.g. `srm.example.org`) with an **A/AAAA record** pointing at the server.
- Ports **80** and **443** open (`ufw allow 80,443/tcp`).
- Docker Engine + the Compose plugin:

  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" && newgrp docker
  ```

## 1. Get the code

```bash
sudo mkdir -p /opt/knsb && sudo chown "$USER" /opt/knsb
git clone https://github.com/asebyrm/knsb-motor-designer /opt/knsb
cd /opt/knsb
```

## 2. Configure `.env`

```bash
cp .env.example .env
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))" >> .env
```

Then edit `.env` and set at least:

| Key | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DOMAIN` | your domain, e.g. `srm.example.org` |
| `ACME_EMAIL` | your email (Let's Encrypt notifications) |
| `POSTGRES_PASSWORD` | a strong random string |
| `SECRET_KEY` | the line generated above (keep only one) |
| `CORS_ORIGINS` | `https://srm.example.org` |

The API **refuses to start in production** without a real `SECRET_KEY` — this is
intentional (Section 12.1). No secret is ever committed; `.env` is git-ignored.

## 3. Bring it up

```bash
docker compose up -d --build
docker compose ps          # api, web, db, caddy should be healthy
docker compose exec api alembic upgrade head   # first-time DB schema
```

Caddy obtains a certificate automatically on first request. Open
`https://<your-domain>` — you should see the designer. Everything (design + simulate +
export + quick altitude estimate) works **without logging in**.

## 4. Create the first admin

The **first account you register becomes an admin** automatically. Open the site,
click *Sign up*, create your account — you now have the *Admin* button in the top bar.

## 5. Operations

```bash
# logs
docker compose logs -f api

# apply new migrations after a pull
git pull && docker compose up -d --build && docker compose exec api alembic upgrade head

# database backup (cron: 0 3 * * *)
COMPOSE="docker compose" ./scripts/backup_db.sh

# prune old export files (cron: 0 * * * *)
OUTPUTS_DIR=/opt/knsb/outputs ./scripts/cleanup_exports.sh
```

Add both scripts to the deploy user's `crontab -e`.

## 6. Scaling knobs (`.env`)

| Key | Meaning | Default |
| --- | --- | --- |
| `API_WORKERS` | Gunicorn/Uvicorn worker processes | 4 |
| `SOLVER_PROCESSES` | `ProcessPoolExecutor` size for the mission solver | 2 |
| `SIM_THREAD_WORKERS` | thread pool for forward simulations | 4 |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | SQLAlchemy pool | 10 / 20 |
| `RATE_LIMIT_*` | per-IP request limits | 5 / 30 / 10 per min |

Never run a single API worker in production — a CPU-bound request would stall the
whole process (Section 12.2). The mission solver already runs in a separate process
pool and returns a `job_id` immediately; the frontend polls `GET /api/jobs/{id}`.

## Advanced monitoring (optional, default OFF)

`docker compose up` does **not** start Prometheus or Grafana. The API always exposes
plain JSON at `/api/admin/stats` (usage counts, DB-only) and `/api/admin/health`
(process RSS, pool queues, disk) and the admin panel draws its own charts from those.

For a full metrics stack:

```bash
docker compose --profile monitoring up -d
```

This adds `prometheus` (scrapes the API's `/metrics`) and `grafana` on port `3000`
(login `admin` / `${GRAFANA_PASSWORD}`). The Prometheus datasource is pre-provisioned;
build dashboards from the `knsb_http_request_seconds` histogram and
`knsb_http_requests_total` counter. Keeping this profile off keeps a small deployment
light.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `FATAL: SECRET_KEY is not set` | put a real `SECRET_KEY` in `.env`, `docker compose up -d` |
| Caddy TLS fails | check the DNS A record and that ports 80/443 are open; `docker compose logs caddy` |
| `no such table` | run `docker compose exec api alembic upgrade head` |
| 408 on `/api/simulate` | raise `SIMULATION_TIMEOUT_S`; check the design isn't pathological |
| mission job stuck `pending` | `SOLVER_PROCESSES` is 0, or the worker crashed — `docker compose logs api` |
