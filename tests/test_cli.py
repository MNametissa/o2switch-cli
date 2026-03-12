from __future__ import annotations

import json

from typer.testing import CliRunner

from o2switch_cli.cli.main import app
from o2switch_cli.core.models import (
    DomainDescriptor,
    DomainType,
    HostnameSearchResult,
    MutationPlan,
    OperationMode,
    OperationResult,
    PlannedAction,
    SearchCategory,
    SubdomainDescriptor,
    VerificationStatus,
)

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


def test_dns_verify_lookup_failure_returns_warning_exit_code(monkeypatch) -> None:
    class FakeDNS:
        def verify_record(self, host: str, ip: str | None = None) -> OperationResult:
            return OperationResult(
                operation="dns_verify",
                mode=OperationMode.DNS_ONLY,
                target=host,
                zone="ginutech.com",
                action="verified",
                applied=False,
                verification=VerificationStatus.LOOKUP_FAILED,
                message="lookup failed",
            )

    class FakeRuntime:
        dns = FakeDNS()

    monkeypatch.setattr("o2switch_cli.cli.context.AppContext.runtime", lambda self: FakeRuntime())
    result = runner.invoke(app, ["--json", "dns", "verify", "--host", "odoo.ginutech.com"])
    payload = json.loads(result.output)
    assert result.exit_code == 7
    assert payload["verification"] == "lookup_failed"


def test_dns_search_json_returns_combined_categories(monkeypatch) -> None:
    class FakeDNS:
        def search(self, term: str) -> list[HostnameSearchResult]:
            return [
                HostnameSearchResult(
                    category=SearchCategory.HOSTED_SUBDOMAINS,
                    hostname="app.ginutech.com",
                    managed_by_cpanel=True,
                    zone="ginutech.com",
                ),
                HostnameSearchResult(
                    category=SearchCategory.DNS_RECORDS,
                    hostname="odoo.ginutech.com",
                    record_type="A",
                    value="203.0.113.25",
                    zone="ginutech.com",
                ),
            ]

    class FakeRuntime:
        dns = FakeDNS()

    monkeypatch.setattr("o2switch_cli.cli.context.AppContext.runtime", lambda self: FakeRuntime())
    result = runner.invoke(app, ["--json", "dns", "search", "ginutech.com"])
    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert {item["category"] for item in payload} == {"hosted_subdomains", "dns_records"}


def test_dns_search_json_returns_available_category(monkeypatch) -> None:
    class FakeDNS:
        def search(self, term: str):
            return [
                HostnameSearchResult(
                    category=SearchCategory.AVAILABLE,
                    hostname=term,
                    zone="ginutech.com",
                )
            ]

    class FakeRuntime:
        dns = FakeDNS()

    monkeypatch.setattr("o2switch_cli.cli.context.AppContext.runtime", lambda self: FakeRuntime())
    result = runner.invoke(app, ["--json", "dns", "search", "free.ginutech.com"])
    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert payload[0]["category"] == "available"


def test_domains_list_json_supports_pagination(monkeypatch) -> None:
    class FakeDomains:
        def list_domains(self) -> list[DomainDescriptor]:
            return [
                DomainDescriptor(domain="a.example.com", type=DomainType.MAIN),
                DomainDescriptor(domain="b.example.com", type=DomainType.ADDON),
            ]

    class FakeRuntime:
        domains = FakeDomains()

    monkeypatch.setattr("o2switch_cli.cli.context.AppContext.runtime", lambda self: FakeRuntime())
    result = runner.invoke(app, ["--json", "domains", "list", "--page", "2", "--page-size", "1"])
    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert [item["domain"] for item in payload] == ["b.example.com"]


def test_subdomains_search_json_supports_pagination(monkeypatch) -> None:
    class FakeSubdomains:
        def search(self, term: str) -> list[SubdomainDescriptor]:
            assert term == "ginutech"
            return [
                SubdomainDescriptor(fqdn="a.ginutech.com", label="a", root_domain="ginutech.com"),
                SubdomainDescriptor(fqdn="b.ginutech.com", label="b", root_domain="ginutech.com"),
            ]

    class FakeRuntime:
        subdomains = FakeSubdomains()

    monkeypatch.setattr("o2switch_cli.cli.context.AppContext.runtime", lambda self: FakeRuntime())
    result = runner.invoke(
        app,
        ["--json", "subdomains", "search", "ginutech", "--page", "1", "--page-size", "1"],
    )
    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert [item["fqdn"] for item in payload] == ["a.ginutech.com"]


def test_dns_verify_mismatch_returns_warning_exit_code(monkeypatch) -> None:
    class FakeDNS:
        def verify_record(self, host: str, ip: str | None = None):
            return OperationResult(
                operation="dns_verify",
                mode=OperationMode.DNS_ONLY,
                target=host,
                zone="ginutech.com",
                action="verified",
                applied=False,
                verification=VerificationStatus.RESOLVED_MISMATCH,
                message="Mismatch",
            )

    class FakeRuntime:
        dns = FakeDNS()

    monkeypatch.setattr("o2switch_cli.cli.context.AppContext.runtime", lambda self: FakeRuntime())
    result = runner.invoke(app, ["--json", "dns", "verify", "--host", "odoo.ginutech.com"])
    assert result.exit_code == 7
