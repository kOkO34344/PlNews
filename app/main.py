"""FastAPI application entrypoint: `uvicorn app.main:app --reload`."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.db import init_db

logging.basicConfig(level=logging.INFO, format="%(message)s")
structlog.configure(processors=[structlog.processors.add_log_level,
                                structlog.processors.TimeStamper(fmt="iso"),
                                structlog.dev.ConsoleRenderer()])

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.app_env == "dev":
        init_db()   # prod uses alembic
    yield


app = FastAPI(
    lifespan=lifespan,
    title="3-3-3 Democracy-Aware News Analyst",
    version="0.1.0",
    description="Daily digest: 3 Bulgarian politics · 3 global politics · 3 AI/tech/business, "
                "with democracy- and bias-aware analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.app_env == "dev" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
