from __future__ import annotations

import pytest

from o2switch_cli.core.audit import AuditService
from o2switch_cli.core.dns_service import DNSService
from o2switch_cli.core.domain_service import DomainService
from o2switch_cli.core.errors import ConflictAppError, ValidationAppError
from o2switch_cli.core.models import ApiResult, SearchCategory, VerificationStatus


class FakeClient:
    def __init__(self, entries: list[dict], hosted: list[dict] | None = None) -> None:
        self.entries = entries
        self.hosted = hosted or []
        self.mass_edit_calls: list[dict] = []

    def list_domains(self) -> ApiResult:
        return ApiResult(data={"main_domain": "ginutech.com", "addon_domains": [], "parked_domains": []})

    def parse_zone(self, zone: str) -> ApiResult:
        assert zone == "ginutech.com"
        return ApiResult(data={"entries": self.entries}, metadata={"serial": 2026031201})

    def mass_edit_zone(self, **kwargs) -> ApiResult:
        self.mass_edit_calls.append(kwargs)
        return ApiResult(data={"ok": True})

    def list_subdomains(self) -> ApiResult:
        return ApiResult(data=self.hosted)


class FakeResolver:
    def verify_a(self, hostname: str, expected_ip: str | None = None) -> tuple[VerificationStatus, list[str]]:
        return VerificationStatus.RESOLVED_MATCHES_TARGET, [expected_ip] if expected_ip else []


def build_service(entries: list[dict], hosted: list[dict] | None = None) -> tuple[FakeClient, DNSService]:
    client = FakeClient(entries, hosted=hosted)
    domains = DomainService(client)  # type: ignore[arg-type]
    service = DNSService(client, domains, FakeResolver(), AuditService(), ["www", "mail"])  # type: ignore[arg-type]
    return client, service


def test_upsert_returns_noop_when_record_matches() -> None:
    _, service = build_service(
        [
            {
                "dname": "odoo",
                "record_type": "A",
                "address": "203.0.113.25",
                "ttl": 300,
                "line_index": 7,
            }
        ]
    )
    plan, result = service.upsert_a_record(
        "odoo.ginutech.com",
        "203.0.113.25",
        300,
        dry_run=False,
        force=False,
        verify=True,
    )
    assert plan.planned_action.value == "no-op"
    assert result.action == "no-op"
    assert result.applied is False


def test_upsert_creates_record_when_missing() -> None:
    client, service = build_service([])
    _, result = service.upsert_a_record(
        "odoo.ginutech.com",
        "203.0.113.25",
        300,
        dry_run=False,
        force=False,
        verify=True,
    )
    assert result.action == "created"
    assert client.mass_edit_calls[0]["zone"] == "ginutech.com"
    assert client.mass_edit_calls[0]["add"][0]["data"] == ["203.0.113.25"]


def test_upsert_rejects_reserved_direct_hostname() -> None:
    _, service = build_service([])
    with pytest.raises(ValidationAppError):
        service.plan_upsert_a_record("mail.ginutech.com", "203.0.113.25", 300, force=False)


def test_upsert_force_normalizes_multiple_records_to_single_add() -> None:
    client, service = build_service(
        [
            {"dname": "odoo", "record_type": "A", "address": "203.0.113.25", "ttl": 300, "line_index": 1},
            {"dname": "odoo", "record_type": "A", "address": "203.0.113.26", "ttl": 300, "line_index": 2},
        ]
    )
    plan, result = service.upsert_a_record(
        "odoo.ginutech.com",
        "203.0.113.99",
        300,
        dry_run=False,
        force=True,
        verify=True,
    )
    assert plan.before is not None
    assert result.action == "updated"
    assert client.mass_edit_calls[0]["remove"] == [1, 2]
    assert client.mass_edit_calls[0]["add"][0]["data"] == ["203.0.113.99"]


def test_delete_rejects_ambiguous_records_without_force() -> None:
    _, service = build_service(
        [
            {"dname": "odoo", "record_type": "A", "address": "203.0.113.25", "ttl": 300, "line_index": 1},
            {"dname": "odoo", "record_type": "A", "address": "203.0.113.26", "ttl": 300, "line_index": 2},
        ]
    )
    with pytest.raises(ConflictAppError):
        service.delete_a_record("odoo.ginutech.com", dry_run=False, force=False, verify=False)


def test_search_combines_hosted_dns_and_available_states() -> None:
    _, service = build_service(
        [{"dname": "odoo", "record_type": "A", "address": "203.0.113.25", "ttl": 300, "line_index": 1}],
        hosted=[{"domain": "app.ginutech.com", "rootdomain": "ginutech.com", "dir": "/public_html/app"}],
    )
    combined = service.search("ginutech.com")
    categories = {item.category for item in combined}
    assert SearchCategory.DNS_RECORDS in categories
    assert SearchCategory.HOSTED_SUBDOMAINS in categories

    available = service.search("free.ginutech.com")
    assert available[0].category is SearchCategory.AVAILABLE


def test_search_returns_available_when_hostname_is_free() -> None:
    _, service = build_service([])
    results = service.search("free.ginutech.com")
    assert results[0].category is SearchCategory.AVAILABLE


def test_forced_upsert_normalizes_multiple_records_into_one() -> None:
    client, service = build_service(
        [
            {"dname": "odoo", "record_type": "A", "address": "203.0.113.25", "ttl": 300, "line_index": 1},
            {"dname": "odoo", "record_type": "A", "address": "203.0.113.26", "ttl": 300, "line_index": 2},
        ]
    )
    _, result = service.upsert_a_record(
        "odoo.ginutech.com",
        "203.0.113.30",
        300,
        dry_run=False,
        force=True,
        verify=True,
    )
    assert result.action == "updated"
    assert client.mass_edit_calls[0]["remove"][0] == 1
    assert client.mass_edit_calls[0]["add"][0]["data"] == ["203.0.113.30"]
