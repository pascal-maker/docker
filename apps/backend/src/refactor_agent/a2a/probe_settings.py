"""Pydantic settings for A2A probe/security-check scripts.

Reads A2A URL from (in order of precedence):
  - Init kwargs (e.g. from CLI)
  - Environment variable A2A_URL
  - Module-scoped dot file .refactor-agent-a2a-url in the repo root (same file
    written by `make infra-a2a-url` and read by the VS Code extension)
  - Default http://localhost:9999

The dot file is a single line (the URL only, no KEY=value). We use a custom
Pydantic settings source to read it; env_file expects KEY=value so we don't use it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

# Repo root: this module is refactor_agent/a2a/probe_settings.py (module-scoped path).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
A2A_URL_DOTFILE = _REPO_ROOT / ".refactor-agent-a2a-url"


class A2aUrlFileSource(PydanticBaseSettingsSource):
    """Read a2a_url from .refactor-agent-a2a-url (single line = URL) if present."""

    def get_field_value(
        self,
        field: "FieldInfo",  # noqa: ARG002, UP037 — base class API; forward ref for TYPE_CHECKING
        field_name: str,
    ) -> tuple[Any, str, bool]:
        """Return a2a_url from dot file if present; else None for this field."""
        if field_name != "a2a_url":
            return None, field_name, False
        if not A2A_URL_DOTFILE.is_file():
            return None, field_name, False
        try:
            value = A2A_URL_DOTFILE.read_text(encoding="utf-8").strip()
        except OSError:
            return None, field_name, False
        if not value:
            return None, field_name, False
        return value, field_name, False

    def __call__(self) -> dict[str, Any]:  # no-dict-sig: PydanticBaseSettingsSource API
        """Return dict of field values read from the dot file."""
        out: dict[str, Any] = {}
        for field_name, field in self.settings_cls.model_fields.items():
            value, key, _ = self.get_field_value(field, field_name)
            if value is not None:
                out[key] = value
        return out


class A2aProbeSettings(BaseSettings):
    """Settings for A2A probe and security-check scripts."""

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        env_file_encoding="utf-8",
    )

    a2a_url: str = "http://localhost:9999"
    api_key: str | None = None
    timeout: float = 15.0

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Init and env override; then dot file; then defaults."""
        return (
            init_settings,
            env_settings,
            A2aUrlFileSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )
