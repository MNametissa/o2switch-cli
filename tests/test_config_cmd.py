from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from o2switch_cli.cli.main import app

runner = CliRunner()


def test_config_init_writes_env_file_non_interactive(tmp_path: Path) -> None:
    target = tmp_path / "custom.env"
    result = runner.invoke(
        app,
        [
            "config",
            "init",
            "--path",
            str(target),
            "--cpanel-host",
            "saule.o2switch.net",
            "--cpanel-user",
            "demo",
            "--cpanel-token",
            "secret-token",
            "--default-ttl",
            "900",
            "--non-interactive",
        ],
    )
    assert result.exit_code == 0
    content = target.read_text(encoding="utf-8")
    assert "O2SWITCH_CLI_CPANEL_HOST=saule.o2switch.net" in content
    assert "O2SWITCH_CLI_CPANEL_USER=demo" in content
    assert "O2SWITCH_CLI_CPANEL_TOKEN=secret-token" in content
    assert "O2SWITCH_CLI_DEFAULT_TTL=900" in content
    assert "O2SWITCH_CLI_AUDIT_LOG_PATH=" in content


def test_config_init_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_text("O2SWITCH_CLI_CPANEL_HOST=old.example\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "config",
            "init",
            "--path",
            str(target),
            "--cpanel-host",
            "saule.o2switch.net",
            "--cpanel-user",
            "demo",
            "--cpanel-token",
            "secret-token",
            "--non-interactive",
        ],
    )
    assert result.exit_code == 2
