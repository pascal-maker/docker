"""Preset config model and loader for CI refactor check."""

from __future__ import annotations

import os
from pathlib import Path  # noqa: TC003 — Path used at runtime for path ops

import yaml
from pydantic import BaseModel, Field


class RefactorAgentPreset(BaseModel):
    """A named preset mapping to a planner goal (and optional language/file_ext)."""

    id: str = Field(description="Unique preset identifier (e.g. layer-boundaries).")
    goal: str = Field(description="Planner goal text for this preset.")
    language: str | None = Field(
        default=None,
        description="Override detected workspace language (e.g. typescript, python).",
    )
    file_ext: str | None = Field(
        default=None,
        description="Override file extension glob (e.g. *.ts, *.py).",
    )
    workspace_subdir: str | None = Field(
        default=None,
        description=(
            "Run this preset under a subdir of the CI workspace (e.g. playground/typescript). "
            "Paths are relative to the workspace root; node_modules is always excluded from scans."
        ),
    )


class RefactorAgentConfig(BaseModel):
    """Root config read from .refactor-agent.yaml (or .yml)."""

    presets: list[RefactorAgentPreset] = Field(
        default_factory=list,
        description="List of presets to run.",
    )


_CONFIG_FILENAMES = (".refactor-agent.yaml", ".refactor-agent.yml")
_ENV_PRESET = "REFACTOR_AGENT_PRESET"
_ENV_GOAL = "REFACTOR_AGENT_GOAL"


def _detect_language(workspace: Path) -> tuple[str, str]:
    """Detect language and file_ext from workspace. Returns (language, file_ext)."""
    if (workspace / "tsconfig.json").exists():
        return "typescript", "*.ts"
    if (workspace / "pyproject.toml").exists() or (workspace / "setup.py").exists():
        return "python", "*.py"
    ts_files = list(workspace.rglob("*.ts"))
    py_files = list(workspace.rglob("*.py"))
    if ts_files and (not py_files or len(ts_files) >= len(py_files)):
        return "typescript", "*.ts"
    return "python", "*.py"


def load_config(
    workspace: Path, config_path: Path | None = None
) -> RefactorAgentConfig:
    """Load RefactorAgentConfig from file under workspace or return empty config.

    When config_path is None, looks under workspace first; if no file found there,
    tries current directory (so repo-root config works when workspace is a subdir).
    """
    if config_path is not None:
        if config_path.exists():
            raw = yaml.safe_load(config_path.read_text()) or {}
            return RefactorAgentConfig.model_validate(raw)
        return RefactorAgentConfig()

    for name in _CONFIG_FILENAMES:
        path = workspace / name
        if path.exists():
            raw = yaml.safe_load(path.read_text()) or {}
            return RefactorAgentConfig.model_validate(raw)
    # Fallback: config at cwd (e.g. repo root when workspace is a subdir).
    cwd = Path.cwd()
    for name in _CONFIG_FILENAMES:
        path = cwd / name
        if path.exists():
            raw = yaml.safe_load(path.read_text()) or {}
            return RefactorAgentConfig.model_validate(raw)
    return RefactorAgentConfig()


def resolve_presets(
    workspace: Path,
    config_path: Path | None = None,
) -> list[RefactorAgentPreset]:
    """Resolve presets from config file and env. Env overrides which presets run.

    If REFACTOR_AGENT_PRESET is set (comma-separated ids), only those presets
    from the config are returned. If REFACTOR_AGENT_GOAL is set and no config
    file exists (or env takes precedence), a single preset with id "env" and
    that goal is returned.
    """
    env_preset = os.environ.get(_ENV_PRESET)
    env_goal = os.environ.get(_ENV_GOAL)

    config = load_config(workspace, config_path)
    file_presets = {p.id: p for p in config.presets}

    if env_goal and not file_presets:
        return [
            RefactorAgentPreset(id="env", goal=env_goal.strip()),
        ]
    if env_preset:
        ids = [s.strip() for s in env_preset.split(",") if s.strip()]
        return [file_presets[pid] for pid in ids if pid in file_presets]
    return config.presets


def get_language_and_ext(
    workspace: Path,
    preset: RefactorAgentPreset,
) -> tuple[str, str]:
    """Return (language, file_ext) for a preset (preset override or detect)."""
    if preset.language is not None and preset.file_ext is not None:
        return preset.language, preset.file_ext
    if preset.language is not None:
        ext = preset.file_ext or ("*.ts" if preset.language == "typescript" else "*.py")
        return preset.language, ext
    if preset.file_ext is not None:
        lang = "typescript" if "*.ts" in preset.file_ext else "python"
        return lang, preset.file_ext
    return _detect_language(workspace)
