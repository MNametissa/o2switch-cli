from __future__ import annotations

import json

from typer.testing import CliRunner

from o2switch_cli.cli.main import app
from o2switch_cli.core.models import MutationPlan, OperationMode, OperationResult, PlannedAction, VerificationStatus

runner = CliRunner()


def test_root_without_command_shows_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Interactive cPanel DNS and hosted subdomain operator." in result.output


def test_config_show_json_redacts_token() -> None:
    result = runner.invoke(
        app,
        ["--json", "config", "show"],
        env={
            "O2SWITCH_CLI_CPANEL_HOST": "cpanel.example.test",
            "O2SWITCH_CLI_CPANEL_USER": "demo",
            "O2SWITCH_CLI_CPANEL_TOKEN": "super-secret-token",
        },
    )
    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert payload["cpanel_token"].startswith("supe...")


def test_dns_upsert_uses_runtime_and_returns_json(monkeypatch) -> None:
    class FakeDNS:
        def plan_upsert_a_record(self, host: str, ip: str, ttl: int, *, force: bool):
            return (
                "ginutech.com",
                None,
                [],
                MutationPlan(
                    operation="dns_upsert",
                    planned_action=PlannedAction.CREATE,
                    summary=f"Create A record {host} -> {ip} (ttl={ttl}).",
                    after={"name": host, "value": ip, "ttl": ttl},
                ),
            )

        def upsert_a_record(self, host: str, ip: str, ttl: int, **_: object):
            result = OperationResult(
                operation="dns_upsert",
                mode=OperationMode.DNS_ONLY,
                target=host,
                zone="ginutech.com",
                action="dry-run",
                applied=False,
                verification=VerificationStatus.SKIPPED,
                planned_action=PlannedAction.CREATE,
                message=f"Create A record {host} -> {ip} (ttl={ttl}).",
                new_value=ip,
                ttl=ttl,
            )
            return self.plan_upsert_a_record(host, ip, ttl, force=False)[3], result

    class FakeRuntime:
        dns = FakeDNS()

    monkeypatch.setattr("o2switch_cli.cli.context.AppContext.runtime", lambda self: FakeRuntime())
    result = runner.invoke(
        app,
        ["--json", "--dry-run", "--yes", "dns", "upsert", "--host", "odoo.ginutech.com", "--ip", "203.0.113.25"],
    )
    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert payload["operation"] == "dns_upsert"
    assert payload["action"] == "dry-run"
