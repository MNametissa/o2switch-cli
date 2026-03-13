from __future__ import annotations

import base64

import pytest

from o2switch_cli.core.audit import AuditService
from o2switch_cli.core.dns_service import DNSService
from o2switch_cli.core.domain_service import DomainService
from o2switch_cli.core.errors import ConflictAppError, TransportAppError, ValidationAppError
from o2switch_cli.core.models import ApiResult, SearchCategory, VerificationStatus


class FakeClient:
    def __init__(
        self,
        entries: list[dict],
        hosted: list[dict] | None = None,
        *,
        serial: int | None = 2026031201,
        domains_payload: dict | None = None,
        zone_entries: dict[str, list[dict]] | None = None,
    ) -> None:
        self.entries = entries
        self.hosted = hosted or []
        self.serial = serial
        self.domains_payload = domains_payload or {
            "main_domain": "ginutech.com",
            "addon_domains": [],
            "parked_domains": [],
        }
        self.zone_entries = zone_entries or {"ginutech.com": entries}
        self.mass_edit_calls: list[dict] = []

    def list_domains(self) -> ApiResult:
        return ApiResult(data=self.domains_payload)

    def parse_zone(self, zone: str) -> ApiResult:
        assert zone in self.zone_entries
        metadata = {"serial": self.serial} if self.serial is not None else {}
        return ApiResult(data={"entries": self.zone_entries[zone]}, metadata=metadata)

    def mass_edit_zone(self, **kwargs) -> ApiResult:
        self.mass_edit_calls.append(kwargs)
        return ApiResult(data={"ok": True})

    def list_subdomains(self) -> ApiResult:
        return ApiResult(data=self.hosted)


class FakeResolver:
    def verify_a(self, hostname: str, expected_ip: str | None = None) -> tuple[VerificationStatus, list[str]]:
        return VerificationStatus.RESOLVED_MATCHES_TARGET, [expected_ip] if expected_ip else []


def build_service(
    entries: list[dict],
    hosted: list[dict] | None = None,
    *,
    serial: int | None = 2026031201,
    domains_payload: dict | None = None,
    zone_entries: dict[str, list[dict]] | None = None,
) -> tuple[FakeClient, DNSService]:
    client = FakeClient(
        entries,
        hosted=hosted,
        serial=serial,
        domains_payload=domains_payload,
        zone_entries=zone_entries,
    )
    domains = DomainService(client)  # type: ignore[arg-type]
    service = DNSService(client, domains, FakeResolver(), AuditService(), ["www", "mail"])  # type: ignore[arg-type]
    return client, service


def b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


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
    assert client.mass_edit_calls[0]["add"][0]["dname"] == "odoo"
    assert client.mass_edit_calls[0]["add"][0]["data"] == ["203.0.113.25"]


def test_upsert_allows_label_input_when_zone_is_selected() -> None:
    client, service = build_service([])
    _, result = service.upsert_a_record(
        "odoo",
        "203.0.113.25",
        300,
        dry_run=False,
        force=False,
        verify=False,
        zone="ginutech.com",
    )
    assert result.target == "odoo.ginutech.com"
    assert client.mass_edit_calls[0]["zone"] == "ginutech.com"
    assert client.mass_edit_calls[0]["add"][0]["dname"] == "odoo"


def test_upsert_auto_selects_longest_matching_dns_zone() -> None:
    client, service = build_service(
        [],
        domains_payload={
            "main_domain": "ginutech.com",
            "addon_domains": [],
            "parked_domains": [],
            "sub_domains": ["event-planner.ginutech.com"],
        },
        zone_entries={
            "ginutech.com": [],
            "event-planner.ginutech.com": [],
        },
    )
    _, result = service.upsert_a_record(
        "api.event-planner.ginutech.com",
        "203.0.113.25",
        300,
        dry_run=False,
        force=False,
        verify=False,
    )
    assert result.zone == "event-planner.ginutech.com"
    assert client.mass_edit_calls[0]["zone"] == "event-planner.ginutech.com"
    assert client.mass_edit_calls[0]["add"][0]["dname"] == "api"


def test_upsert_rejects_hostnames_outside_selected_zone() -> None:
    _, service = build_service([])
    with pytest.raises(ValidationAppError):
        service.upsert_a_record(
            "odoo.example.com",
            "203.0.113.25",
            300,
            dry_run=False,
            force=False,
            verify=False,
            zone="ginutech.com",
        )


def test_upsert_rejects_reserved_direct_hostname() -> None:
    _, service = build_service([])
    with pytest.raises(ValidationAppError):
        service.plan_upsert_a_record("mail.ginutech.com", "203.0.113.25", 300, force=False)


def test_upsert_refuses_live_write_when_zone_serial_is_missing() -> None:
    _, service = build_service([], serial=None)
    with pytest.raises(TransportAppError):
        service.upsert_a_record(
            "odoo.ginutech.com",
            "203.0.113.25",
            300,
            dry_run=False,
            force=False,
            verify=False,
        )


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


def test_upsert_extracts_serial_from_base64_soa_record() -> None:
    client, service = build_service(
        [
            {
                "dname_b64": b64("ginutech.com."),
                "record_type": "SOA",
                "data_b64": [
                    b64("ns1.o2switch.net."),
                    b64("sysadmin.o2switch.fr."),
                    b64("2026031100"),
                    b64("3600"),
                    b64("1800"),
                    b64("1209600"),
                    b64("86400"),
                ],
                "ttl": 86400,
                "line_index": 3,
            }
        ],
        serial=None,
    )
    _, result = service.upsert_a_record(
        "odoo.ginutech.com",
        "203.0.113.25",
        300,
        dry_run=False,
        force=False,
        verify=False,
    )
    assert result.action == "created"
    assert client.mass_edit_calls[0]["serial"] == 2026031100


def test_find_records_decodes_base64_zone_entries() -> None:
    _, service = build_service(
        [
            {
                "dname_b64": b64("odoo.ginutech.com."),
                "record_type": "A",
                "data_b64": [b64("203.0.113.25")],
                "ttl": 300,
                "line_index": 7,
            }
        ],
        serial=None,
    )
    matches = service.find_records("odoo.ginutech.com")
    assert len(matches) == 1
    assert matches[0].name == "odoo.ginutech.com"
    assert matches[0].value == "203.0.113.25"


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


def test_delete_refuses_live_write_when_zone_serial_is_missing() -> None:
    _, service = build_service(
        [{"dname": "odoo", "record_type": "A", "address": "203.0.113.25", "ttl": 300, "line_index": 1}],
        serial=None,
    )
    with pytest.raises(TransportAppError):
        service.delete_a_record("odoo.ginutech.com", dry_run=False, force=False, verify=False)
