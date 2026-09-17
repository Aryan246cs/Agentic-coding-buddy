"""The API.

Run it with:  uv run uvicorn app.main:app --reload --app-dir apps/api
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import create_all
from app.routers import auth, projects, runtime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.is_production:
        # Convenient locally. Production migrates with Alembic instead.
        create_all()
    logger.info(
        "started in %s mode — database %s, AI provider %s",
        settings.environment,
        settings.database_url.split("://", 1)[0],
        settings.resolved_provider,
    )
    yield


app = FastAPI(
    title="Workflow Platform API",
    version="0.1.0",
    summary="Describe how your work happens. Get a working system with a link.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def readable_validation_errors(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """Turn FastAPI's validation output into something a person can read.

    The app's users are not developers, and `body -> data -> days -> int_parsing`
    is not a sentence.
    """
    field_errors: dict[str, str] = {}
    for error in exc.errors():
        parts = [str(part) for part in error["loc"] if part not in ("body", "query")]
        where = parts[-1] if parts else "request"
        field_errors[where] = error["msg"]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": {
                "message": "Please check what you sent.",
                "field_errors": field_errors,
            }
        },
    )


app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(runtime.router)
app.include_router(runtime.site_router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, object]:
    return {
        "ok": True,
        "environment": settings.environment,
        "ai_provider": settings.resolved_provider,
    }
