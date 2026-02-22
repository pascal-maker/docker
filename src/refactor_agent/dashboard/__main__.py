"""Run the dashboard when invoked as python -m refactor_agent.dashboard."""

from __future__ import annotations

import os
from pathlib import Path

from refactor_agent.dashboard.main import run_dashboard

if __name__ == "__main__":
    db_path = os.environ.get("REFACTOR_AGENT_DASHBOARD_DB")
    run_dashboard(
        db_path=Path(db_path) if db_path else None,
    )
