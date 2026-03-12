from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr

from o2switch_cli.config.settings import AppSettings, default_audit_log_path, render_env_file, write_env_file


def test_render_env_file_includes_expected_keys() -> None:
    settings = AppSettings(
        cpanel_host="saule.o2switch.net",
        cpanel_user="demo",
        cpanel_token=SecretStr("secret-token"),
        default_ttl=300,
        audit_log_path="/tmp/o2switch-cli-audit.log",
    )
    rendered = render_env_file(settings)
    assert "O2SWITCH_CLI_CPANEL_HOST=saule.o2switch.net" in rendered
    assert "O2SWITCH_CLI_CPANEL_USER=demo" in rendered
    assert "O2SWITCH_CLI_CPANEL_TOKEN=secret-token" in rendered
    assert "O2SWITCH_CLI_AUDIT_LOG_PATH=/tmp/o2switch-cli-audit.log" in rendered


def test_default_audit_log_path_looks_like_app_state_path() -> None:
    path = default_audit_log_path()
    assert path.endswith("audit.jsonl")
    assert "o2switch-cli" in path


def test_write_env_file_creates_target(tmp_path: Path) -> None:
    settings = AppSettings(
        cpanel_host="saule.o2switch.net",
        cpanel_user="demo",
        cpanel_token=SecretStr("secret-token"),
    )
    target = write_env_file(tmp_path / ".env", settings)
    assert target.exists()
    assert "O2SWITCH_CLI_CPANEL_HOST=saule.o2switch.net" in target.read_text(encoding="utf-8")
