"""ZAI application entrypoint."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import settings
from app.logging_conf import configure, request_id_var

configure(settings.log_level, settings.log_format)
log = logging.getLogger("zai")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0-poc",
    description="Executive Humanitarian Intelligence Platform — prototype API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlate(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - started) * 1000
    response.headers["x-request-id"] = rid
    if not request.url.path.startswith("/api/health"):
        log.info("%s %s -> %s in %.1fms", request.method, request.url.path,
                 response.status_code, elapsed)
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal error", "request_id": request_id_var.get()},
    )


app.include_router(router, prefix="/api")


@app.on_event("startup")
def warm() -> None:
    """Pre-build the dataset so the first executive question is not the slowest."""
    from app.data.repository import load_projects, vocabulary
    rows = load_projects(settings.dataset_size)
    vocabulary(settings.dataset_size)
    log.info("dataset warm: %d projects, providers ready", len(rows))
