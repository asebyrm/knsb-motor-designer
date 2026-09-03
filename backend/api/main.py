"""FastAPI application factory (Sections 3, 12, 12.2).

* lifespan starts/stops the thread + process pools;
* every response carries an ``X-Request-ID``; logs are structured JSON (structlog);
* CPU-bound work never runs directly in an ``async def`` (see ``services.executors``);
* ``/api`` for the API, ``/metrics`` when ``prometheus-client`` instrumentation is on,
  static frontend + generated exports served from disk.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import admin, auth, designs, export, health, mission, simulate
from app_config import get_settings
from models.base import create_all
from services.executors import shutdown_pools, start_pools

settings = get_settings()


def _configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    start_pools()
    if settings.database_url.startswith("sqlite"):
        create_all()  # dev/test convenience; prod uses alembic
    yield
    shutdown_pools()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.4.0",
        summary="KNSB solid rocket motor design & internal-ballistics API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    log = structlog.get_logger("api")

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-ID"] = rid
        log.info("request", method=request.method, status=response.status_code,
                 duration_ms=round((time.perf_counter() - start) * 1000, 1))
        return response

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):  # pragma: no cover - safety net
        log.exception("unhandled")
        return JSONResponse(status_code=500, content={"detail": "internal error"})

    api = FastAPI(title=f"{settings.app_name} API")
    for module in (health, auth, designs, simulate, mission, export, admin):
        api.include_router(module.router)
    api.include_router(designs.public_router)
    app.mount("/api", api)

    _maybe_prometheus(app)
    _maybe_static(app)
    return app


def _maybe_prometheus(app: FastAPI) -> None:
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    except ImportError:  # pragma: no cover
        return
    from fastapi import Response

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _maybe_static(app: FastAPI) -> None:
    import os

    from fastapi.staticfiles import StaticFiles

    if os.path.isdir(settings.outputs_dir):
        app.mount("/outputs", StaticFiles(directory=settings.outputs_dir), name="outputs")
    dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    if os.path.isdir(dist):
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")


app = create_app()
