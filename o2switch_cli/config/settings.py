from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_RESERVED_LABELS = [
    "www",
    "mail",
    "ftp",
    "cpanel",
    "webmail",
    "autodiscover",
]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="O2SWITCH_CLI_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    cpanel_host: str | None = None
    cpanel_user: str | None = None
    cpanel_token: SecretStr | None = None
    port: int = 2083
    timeout_seconds: float = 20.0
    default_ttl: int = 300
    verify_dns_after_mutation: bool = True
    reserved_labels: list[str] = Field(default_factory=lambda: list(DEFAULT_RESERVED_LABELS))
    output_format: Literal["text", "json"] = "text"
    audit_log_path: str | None = None


def _read_config_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8")
    if suffix == ".json":
        return json.loads(raw)
    if suffix in {".toml", ".tml"}:
        return tomllib.loads(raw)
    raise ValueError(f"Unsupported config format: {path.suffix}")


def load_settings(config_path: str | Path | None = None) -> AppSettings:
    overrides: dict[str, Any] = {}
    if config_path:
        path = Path(config_path).expanduser().resolve()
        overrides = _read_config_file(path)
    return AppSettings(**overrides)


def settings_summary(settings: AppSettings) -> dict[str, Any]:
    token = settings.cpanel_token.get_secret_value() if settings.cpanel_token else None
    redacted = None
    if token:
        redacted = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "****"
    return {
        "cpanel_host": settings.cpanel_host,
        "cpanel_user": settings.cpanel_user,
        "cpanel_token": redacted,
        "port": settings.port,
        "timeout_seconds": settings.timeout_seconds,
        "default_ttl": settings.default_ttl,
        "verify_dns_after_mutation": settings.verify_dns_after_mutation,
        "reserved_labels": settings.reserved_labels,
        "output_format": settings.output_format,
        "audit_log_path": settings.audit_log_path,
    }
