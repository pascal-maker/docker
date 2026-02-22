"""FastAPI app for the refactor-issues dashboard (ingestion + query + SPA)."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from refactor_agent.dashboard.ingest import router as ingest_router
from refactor_agent.dashboard.routes.issues import router as issues_router

DEFAULT_DB_PATH = Path("dashboard.db")
DEFAULT_PORT = 8000


def _spa_dist_path() -> Path | None:
    """Path to dashboard-ui/dist (built SPA); None if not present."""
    # From src/refactor_agent/dashboard/main.py -> repo root -> dashboard-ui/dist
    repo_root = Path(__file__).resolve().parents[3]
    dist = repo_root / "dashboard-ui" / "dist"
    return dist if dist.is_dir() else None


def create_app(
    db_path: Path | None = None,
    ingest_api_key: str | None = None,
) -> FastAPI:
    """Create and configure the dashboard FastAPI application."""
    from refactor_agent.dashboard.storage import init_db

    app = FastAPI(
        title="Refactor issues dashboard",
        description="Ingestion and query API for refactor/architecture check results.",
    )
    actual_db = db_path or DEFAULT_DB_PATH
    init_db(actual_db)
    app.state.db_path = actual_db
    app.state.ingest_api_key = ingest_api_key or os.environ.get(
        "REFACTOR_AGENT_INGEST_API_KEY"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ingest_router)
    app.include_router(issues_router)

    dist = _spa_dist_path()
    if dist is not None:
        assets = dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")
        index_html = dist / "index.html"
        if index_html.is_file():

            @app.get("/")
            def _serve_index() -> FileResponse:
                return FileResponse(index_html)

            @app.get("/{rest:path}")
            def _serve_spa(rest: str) -> FileResponse:
                return FileResponse(index_html)

    return app


def run_dashboard(
    host: str = "0.0.0.0",
    port: int | None = None,
    db_path: Path | None = None,
    ingest_api_key: str | None = None,
) -> None:
    """Run the dashboard with uvicorn."""
    port = port or int(os.environ.get("REFACTOR_AGENT_DASHBOARD_PORT", DEFAULT_PORT))
    app = create_app(db_path=db_path, ingest_api_key=ingest_api_key)
    uvicorn.run(app, host=host, port=port)
