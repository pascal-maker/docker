"""Git infra: branch per run, commit per phase, reset on failure."""

from __future__ import annotations

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 — Path used at runtime

from refactor_agent.agentic.logger import logger


def _is_git_repo(workspace: Path) -> bool:
    """Return True if workspace is inside a git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],  # noqa: S607
            cwd=workspace,
            check=True,
            capture_output=True,
            timeout=5,
        )
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return False
    else:
        return True


def _slug_from_goal(goal: str) -> str:
    """Produce a branch-name-safe slug from a refactor goal."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", goal.strip().lower()).strip("-")[:40]
    return slug or "refactor"


def ensure_refactor_branch(workspace: Path, goal: str) -> str | None:
    """Create branch refactor/<slug>-<timestamp> from current HEAD.

    Returns error message or None on success.
    """
    if not _is_git_repo(workspace):
        return None
    slug = _slug_from_goal(goal)
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    branch = f"refactor/{slug}-{ts}"
    try:
        subprocess.run(  # noqa: S603
            ["git", "checkout", "-b", branch],  # noqa: S607
            cwd=workspace,
            check=True,
            capture_output=True,
            timeout=10,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode(errors="replace").strip() or str(e)
        return f"git checkout -b failed: {err}"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return f"git checkout -b failed: {e}"
    else:
        logger.info("Created refactor branch", branch=branch, goal=goal[:80])
        return None


def commit_checkpoint(workspace: Path, message: str) -> str | None:
    """Commit current changes with the given message.

    Returns error message or None on success.
    """
    if not _is_git_repo(workspace):
        return None
    try:
        subprocess.run(
            ["git", "add", "-A"],  # noqa: S607
            cwd=workspace,
            check=True,
            capture_output=True,
            timeout=10,
        )
        subprocess.run(  # noqa: S603
            ["git", "commit", "--allow-empty", "-m", message],  # noqa: S607
            cwd=workspace,
            check=True,
            capture_output=True,
            timeout=10,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode(errors="replace").strip() or str(e)
        return f"git commit failed: {err}"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return f"git commit failed: {e}"
    else:
        logger.info("Committed checkpoint", message=message[:80])
        return None


def reset_to_last_commit(workspace: Path) -> str | None:
    """Reset workspace to last commit (git reset --hard).

    Returns error message or None on success.
    """
    if not _is_git_repo(workspace):
        return None
    try:
        subprocess.run(
            ["git", "reset", "--hard", "HEAD"],  # noqa: S607
            cwd=workspace,
            check=True,
            capture_output=True,
            timeout=10,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or b"").decode(errors="replace").strip() or str(e)
        return f"git reset --hard failed: {err}"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return f"git reset --hard failed: {e}"
    else:
        logger.info("Reset to last commit")
        return None
