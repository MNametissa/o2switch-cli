from __future__ import annotations

import pytest

from o2switch_cli.core.audit import AuditService
from o2switch_cli.core.dns_service import DNSService
from o2switch_cli.core.domain_service import DomainService
from o2switch_cli.core.errors import ConflictAppError
from o2switch_cli.core.models import ApiResult, VerificationStatus


class FakeClient:
    def __init__(self, entries: list[dict]) -> None:
        self.entries = entries
        self.mass_edit_calls: list[dict] = []

    def list_domains(self) -> ApiResult:
        return ApiResult(data={"main_domain": "ginutech.com", "addon_domains": [], "parked_domains": []})

    def parse_zone(self, zone: str) -> ApiResult:
        assert zone == "ginutech.com"
        return ApiResult(data={"entries": self.entries}, metadata={"serial": 2026031201})

    def mass_edit_zone(self, **kwargs) -> ApiResult:
        self.mass_edit_calls.append(kwargs)
        return ApiResult(data={"ok": True})


class FakeResolver:
    def verify_a(self, hostname: str, expected_ip: str | None = None) -> tuple[VerificationStatus, list[str]]:
        return VerificationStatus.RESOLVED_MATCHES_TARGET, [expected_ip] if expected_ip else []


def build_service(entries: list[dict]) -> tuple[FakeClient, DNSService]:
    client = FakeClient(entries)
    domains = DomainService(client)  # type: ignore[arg-type]
    service = DNSService(client, domains, FakeResolver(), AuditService())  # type: ignore[arg-type]
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
    assert client.mass_edit_calls[0]["add"][0]["address"] == "203.0.113.25"


def test_delete_rejects_ambiguous_records_without_force() -> None:
    _, service = build_service(
        [
            {"dname": "odoo", "record_type": "A", "address": "203.0.113.25", "ttl": 300, "line_index": 1},
            {"dname": "odoo", "record_type": "A", "address": "203.0.113.26", "ttl": 300, "line_index": 2},
        ]
    )
    with pytest.raises(ConflictAppError):
        service.delete_a_record("odoo.ginutech.com", dry_run=False, force=False, verify=False)
