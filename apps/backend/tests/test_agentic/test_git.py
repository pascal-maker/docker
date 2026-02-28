"""Tests for git infrastructure."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

try:
    subprocess.run(
        ["git", "--version"],  # noqa: S607
        capture_output=True,
        check=True,
    )
except (subprocess.CalledProcessError, FileNotFoundError):
    pytest.skip("git not available", allow_module_level=True)

from refactor_agent.agentic.git import (
    commit_checkpoint,
    ensure_refactor_branch,
    reset_to_last_commit,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo in tmp_path."""
    subprocess.run(
        ["git", "init"],  # noqa: S607
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "README").write_text("initial")
    subprocess.run(
        ["git", "add", "README"],  # noqa: S607
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],  # noqa: S607
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


def test_ensure_refactor_branch_creates_branch(git_repo: Path) -> None:
    """ensure_refactor_branch creates refactor/<slug>-<timestamp>."""
    err = ensure_refactor_branch(git_repo, "move foo to bar")
    assert err is None
    result = subprocess.run(
        ["git", "branch", "--show-current"],  # noqa: S607
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip().startswith("refactor/")
    assert "move-foo-to-bar" in result.stdout or "refactor" in result.stdout


def test_ensure_refactor_branch_non_repo_returns_none(tmp_path: Path) -> None:
    """ensure_refactor_branch returns None (no error) when not a git repo."""
    err = ensure_refactor_branch(tmp_path, "test")
    assert err is None


def test_commit_checkpoint(git_repo: Path) -> None:
    """commit_checkpoint commits changes."""
    (git_repo / "new.txt").write_text("new content")
    err = commit_checkpoint(git_repo, "refactor: add new.txt")
    assert err is None
    result = subprocess.run(
        ["git", "log", "-1", "--oneline"],  # noqa: S607
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "refactor: add new.txt" in result.stdout


def test_commit_checkpoint_non_repo_returns_none(tmp_path: Path) -> None:
    """commit_checkpoint returns None when not a git repo."""
    err = commit_checkpoint(tmp_path, "test")
    assert err is None


def test_reset_to_last_commit(git_repo: Path) -> None:
    """reset_to_last_commit discards uncommitted changes to tracked files."""
    (git_repo / "README").write_text("modified")
    err = reset_to_last_commit(git_repo)
    assert err is None
    assert (git_repo / "README").read_text() == "initial"


def test_reset_to_last_commit_non_repo_returns_none(tmp_path: Path) -> None:
    """reset_to_last_commit returns None when not a git repo."""
    err = reset_to_last_commit(tmp_path)
    assert err is None
