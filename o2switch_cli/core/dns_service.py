from __future__ import annotations

import base64
import binascii

from o2switch_cli.core.audit import AuditService
from o2switch_cli.core.cpanel_client import CpanelClient
from o2switch_cli.core.domain_service import DomainService
from o2switch_cli.core.errors import ConflictAppError, NotFoundAppError, TransportAppError, ValidationAppError
from o2switch_cli.core.models import (
    DNSRecord,
    HostnameSearchResult,
    MutationPlan,
    OperationMode,
    OperationResult,
    PlannedAction,
    SearchCategory,
    SubdomainDescriptor,
    VerificationStatus,
)
from o2switch_cli.core.validators import (
    canonical_record_name,
    fqdn_for_label,
    normalize_hostname,
    relative_name,
    validate_ipv4,
    validate_reserved_hostname,
    validate_ttl,
)
from o2switch_cli.infra.resolver import DNSResolver


class DNSService:
    def __init__(
        self,
        client: CpanelClient,
        domains: DomainService,
        resolver: DNSResolver,
        audit: AuditService,
        reserved_labels: list[str],
    ) -> None:
        self._client = client
        self._domains = domains
        self._resolver = resolver
        self._audit = audit
        self._reserved_labels = reserved_labels

    @staticmethod
    def _line_index(record: DNSRecord) -> int:
        raw_value = record.record_id or record.raw.get("line_index") or record.raw.get("line")
        return int(raw_value)

    @staticmethod
    def _decode_b64_text(value: object) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError):
            return None
        try:
            return decoded.decode("utf-8")
        except UnicodeDecodeError:
            return decoded.decode("utf-8", errors="replace")

    @classmethod
    def _record_values(cls, item: dict[str, object]) -> list[str]:
        data = item.get("data")
        if isinstance(data, list):
            return [str(value) for value in data]
        if data not in (None, ""):
            return [str(data)]

        data_b64 = item.get("data_b64")
        if isinstance(data_b64, list):
            return [decoded for value in data_b64 if (decoded := cls._decode_b64_text(value)) is not None]
        if decoded := cls._decode_b64_text(data_b64):
            return [decoded]
        return []

    @classmethod
    def _record_name(cls, item: dict[str, object], root_domain: str) -> str:
        raw_name = item.get("dname") or item.get("name") or item.get("domain")
        if raw_name in (None, ""):
            raw_name = cls._decode_b64_text(item.get("dname_b64")) or root_domain
        return canonical_record_name(str(raw_name), root_domain)

    @staticmethod
    def _require_serial(operation: str, root_domain: str, serial: int | None) -> int:
        if serial is None:
            raise TransportAppError(
                operation,
                f"Could not determine the current DNS serial for zone {root_domain}.",
            )
        return serial

    def _zone_state(self, root_domain: str) -> tuple[list[DNSRecord], int | None]:
        result = self._client.parse_zone(root_domain)
        payload = result.data or {}
        entries = []
        metadata = result.metadata
        if isinstance(payload, dict):
            entries = (
                payload.get("entries") or payload.get("records") or payload.get("data") or payload.get("zone") or []
            )
            if not metadata and isinstance(payload.get("metadata"), dict):
                metadata = payload.get("metadata")
        elif isinstance(payload, list):
            entries = payload

        records: list[DNSRecord] = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            record_type = str(item.get("record_type") or item.get("type") or "").upper()
            values = self._record_values(item)
            value = (
                item.get("address")
                or item.get("target")
                or item.get("exchange")
                or item.get("cname")
                or (values[0] if values else "")
            )
            ttl = item.get("ttl")
            record_id = item.get("line_index") or item.get("line") or item.get("record_id") or item.get("id")
            name = self._record_name(item, root_domain)
            records.append(
                DNSRecord(
                    name=name,
                    type=record_type,
                    value=str(value).rstrip("."),
                    ttl=int(ttl) if ttl not in (None, "") else None,
                    zone=normalize_hostname(root_domain),
                    record_id=str(record_id) if record_id is not None else None,
                    raw=item,
                )
            )

        serial = metadata.get("serial") if isinstance(metadata, dict) else None
        if serial is None:
            serial = self._extract_serial(records)
        return records, int(serial) if serial not in (None, "") else None

    @staticmethod
    def _extract_serial(records: list[DNSRecord]) -> int | None:
        for record in records:
            if record.type != "SOA":
                continue
            values = DNSService._record_values(record.raw)
            for value in values:
                if str(value).isdigit() and len(str(value)) >= 8:
                    return int(value)
        return None

    def get_zone_state(self, root_domain: str) -> list[DNSRecord]:
        records, _ = self._zone_state(root_domain)
        return records

    def _resolve_hostname_for_zone(self, hostname_or_label: str, operation: str, zone: str | None = None) -> str:
        candidate = hostname_or_label.strip().lower().rstrip(".")
        if zone is None:
            return normalize_hostname(candidate)

        selected_zone = normalize_hostname(zone)
        if not candidate or candidate == "@":
            return selected_zone

        normalized_candidate = normalize_hostname(candidate)
        if "." in normalized_candidate:
            if normalized_candidate == selected_zone or normalized_candidate.endswith(f".{selected_zone}"):
                return normalized_candidate
            raise ValidationAppError(
                operation,
                "Hostname does not belong to the selected DNS zone.",
                normalized_candidate,
            )
        return fqdn_for_label(normalized_candidate, selected_zone)

    def _resolve_dns_zone(self, hostname: str, operation: str, zone: str | None = None) -> str:
        if zone is None:
            return self._domains.resolve_dns_zone(hostname, operation)

        selected_zone = normalize_hostname(zone)
        descriptor = self._domains.get_domain_descriptor(selected_zone, operation)
        if not descriptor.has_dns_zone:
            raise NotFoundAppError(operation, "The selected domain does not expose a DNS zone.", selected_zone)
        if hostname != selected_zone and not hostname.endswith(f".{selected_zone}"):
            raise ValidationAppError(
                operation,
                "Hostname does not belong to the selected DNS zone.",
                hostname,
            )
        return selected_zone

    @staticmethod
    def _mutation_dname(hostname: str, zone: str) -> str:
        return relative_name(hostname, zone) or "@"

    def find_records(self, fqdn: str, record_type: str = "A") -> list[DNSRecord]:
        hostname = normalize_hostname(fqdn)
        root_domain = self._domains.resolve_dns_zone(hostname, "dns_find")
        records, _ = self._zone_state(root_domain)
        return [item for item in records if item.name == hostname and item.type == record_type.upper()]

    def _hosted_subdomains(self, term: str) -> list[SubdomainDescriptor]:
        needle = term.strip().lower()
        descriptors: list[SubdomainDescriptor] = []
        try:
            payload = self._client.list_subdomains().data or []
        except TransportAppError:
            payload = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            fqdn = normalize_hostname(str(row.get("domain") or row.get("fullsubdomain") or ""))
            if not fqdn or (needle and needle not in fqdn):
                continue
            try:
                root_domain = self._domains.resolve_root_domain(fqdn, "dns_search")
            except NotFoundAppError:
                continue
            descriptors.append(
                SubdomainDescriptor(
                    fqdn=fqdn,
                    label=fqdn[: -(len(root_domain) + 1)],
                    root_domain=root_domain,
                    docroot=str(row.get("dir") or row.get("documentroot") or ""),
                    managed_by_cpanel=True,
                )
            )
        if descriptors:
            return sorted(descriptors, key=lambda item: item.fqdn)

        for item in self._domains.list_domains():
            if item.type.value != "subdomain":
                continue
            if needle and needle not in item.domain:
                continue
            try:
                root_domain = self._domains.resolve_root_domain(item.domain, "dns_search")
            except NotFoundAppError:
                continue
            descriptors.append(
                SubdomainDescriptor(
                    fqdn=item.domain,
                    label=item.domain[: -(len(root_domain) + 1)],
                    root_domain=root_domain,
                    managed_by_cpanel=True,
                )
            )
        return sorted(descriptors, key=lambda item: item.fqdn)

    def search(self, term: str) -> list[HostnameSearchResult]:
        needle = term.strip().lower()
        matches: list[HostnameSearchResult] = []
        for hosted in self._hosted_subdomains(term):
            matches.append(
                HostnameSearchResult(
                    category=SearchCategory.HOSTED_SUBDOMAINS,
                    hostname=hosted.fqdn,
                    managed_by_cpanel=True,
                    zone=hosted.root_domain,
                    docroot=hosted.docroot,
                )
            )
        for root_domain in self._domains.root_domains():
            try:
                records, _ = self._zone_state(root_domain)
            except TransportAppError:
                continue
            for item in records:
                if needle in item.name.lower() or needle in item.value.lower():
                    matches.append(
                        HostnameSearchResult(
                            category=SearchCategory.DNS_RECORDS,
                            hostname=item.name,
                            record_type=item.type,
                            value=item.value,
                            managed_by_cpanel=False,
                            zone=item.zone,
                        )
                    )
        if matches:
            return sorted(matches, key=lambda item: (item.hostname, item.category.value, item.record_type or ""))
        try:
            hostname = normalize_hostname(term)
        except Exception:
            return []
        if "." not in hostname:
            return []
        try:
            root_domain = self._domains.resolve_dns_zone(hostname, "dns_search")
        except NotFoundAppError:
            return []
        return [
            HostnameSearchResult(
                category=SearchCategory.AVAILABLE,
                hostname=hostname,
                managed_by_cpanel=False,
                zone=root_domain,
            )
        ]

    def plan_upsert_a_record(
        self, fqdn: str, ip: str, ttl: int, *, force: bool, zone: str | None = None
    ) -> tuple[str, int | None, list[DNSRecord], MutationPlan]:
        hostname = self._resolve_hostname_for_zone(fqdn, "dns_upsert", zone=zone)
        ipv4 = validate_ipv4(ip)
        resolved_ttl = validate_ttl(ttl, ttl)
        root_domain = self._resolve_dns_zone(hostname, "dns_upsert", zone=zone)
        validate_reserved_hostname(hostname, root_domain, self._reserved_labels)
        records, serial = self._zone_state(root_domain)
        matches = [item for item in records if item.name == hostname and item.type == "A"]
        plan = self._build_upsert_plan(hostname, ipv4, resolved_ttl, matches, force=force)
        return root_domain, serial, matches, plan

    def _build_upsert_plan(
        self, fqdn: str, ip: str, ttl: int, records: list[DNSRecord], *, force: bool
    ) -> MutationPlan:
        if not records:
            return MutationPlan(
                operation="dns_upsert",
                planned_action=PlannedAction.CREATE,
                after={"name": fqdn, "type": "A", "value": ip, "ttl": ttl},
                summary=f"Create A record {fqdn} -> {ip} (ttl={ttl}).",
            )
        if len(records) > 1 and not force:
            raise ConflictAppError("dns_upsert", "Multiple A records already exist for the hostname.", fqdn)
        if len(records) > 1 and force:
            return MutationPlan(
                operation="dns_upsert",
                planned_action=PlannedAction.UPDATE,
                before={"records": [record.model_dump() for record in records]},
                after={"name": fqdn, "type": "A", "value": ip, "ttl": ttl},
                requires_force=True,
                summary=f"Normalize {len(records)} A records for {fqdn} to a single target {ip} (ttl={ttl}).",
            )
        if len(records) == 1 and records[0].value == ip and records[0].ttl == ttl:
            return MutationPlan(
                operation="dns_upsert",
                planned_action=PlannedAction.NOOP,
                before=records[0].model_dump(),
                after=records[0].model_dump(),
                requires_confirmation=False,
                summary="The requested A record already exists with the desired TTL.",
            )
        before = [record.model_dump() for record in records]
        return MutationPlan(
            operation="dns_upsert",
            planned_action=PlannedAction.UPDATE if records else PlannedAction.CREATE,
            before=before[0] if len(before) == 1 else {"records": before} if before else None,
            after={"name": fqdn, "type": "A", "value": ip, "ttl": ttl},
            requires_force=len(records) > 1,
            summary=f"Upsert A record {fqdn} -> {ip} (ttl={ttl}).",
        )

    def upsert_a_record(
        self,
        fqdn: str,
        ip: str,
        ttl: int,
        *,
        dry_run: bool,
        force: bool,
        verify: bool,
        zone: str | None = None,
        mode: OperationMode = OperationMode.DNS_ONLY,
    ) -> tuple[MutationPlan, OperationResult]:
        hostname = self._resolve_hostname_for_zone(fqdn, "dns_upsert", zone=zone)
        ipv4 = validate_ipv4(ip)
        resolved_ttl = validate_ttl(ttl, ttl)
        root_domain, serial, matches, plan = self.plan_upsert_a_record(
            hostname,
            ipv4,
            resolved_ttl,
            force=force,
            zone=zone,
        )

        if plan.planned_action is PlannedAction.NOOP:
            result = OperationResult(
                operation="dns_upsert",
                mode=mode,
                target=hostname,
                zone=root_domain,
                action="no-op",
                applied=False,
                verification=VerificationStatus.SKIPPED,
                planned_action=plan.planned_action,
                old_value=matches[0].value,
                new_value=matches[0].value,
                ttl=matches[0].ttl,
                before=plan.before,
                after=plan.after,
                message=plan.summary,
            )
            return plan, result

        verification = VerificationStatus.SKIPPED
        applied = False
        action = "dry-run" if dry_run else "created"
        if not dry_run:
            serial = self._require_serial("dns_upsert", root_domain, serial)
            mutation_name = self._mutation_dname(hostname, root_domain)
            add = None
            edit = None
            remove = None
            if len(matches) > 1:
                action = "updated"
                remove = [self._line_index(record) for record in matches]
                add = [{"record_type": "A", "dname": mutation_name, "ttl": resolved_ttl, "data": [ipv4]}]
            elif matches:
                action = "updated"
                edit = [
                    {
                        "line_index": self._line_index(record),
                        "record_type": "A",
                        "dname": mutation_name,
                        "ttl": resolved_ttl,
                        "data": [ipv4],
                    }
                    for record in matches
                ]
            else:
                add = [{"record_type": "A", "dname": mutation_name, "ttl": resolved_ttl, "data": [ipv4]}]
            self._client.mass_edit_zone(zone=root_domain, serial=serial, add=add, edit=edit, remove=remove)
            applied = True
            if verify:
                verification, _ = self._resolver.verify_a(hostname, ipv4)
            else:
                verification = VerificationStatus.ACCEPTED_PENDING_VISIBILITY
        result = OperationResult(
            operation="dns_upsert",
            mode=mode,
            target=hostname,
            zone=root_domain,
            action=action,
            applied=applied,
            verification=verification if applied else VerificationStatus.SKIPPED,
            planned_action=plan.planned_action,
            old_value=matches[0].value if len(matches) == 1 else None,
            new_value=ipv4,
            ttl=resolved_ttl,
            before=plan.before,
            after=plan.after,
            message=plan.summary,
        )
        self._audit.record(
            mode=mode,
            operation=result.action,
            hostname=hostname,
            zone=root_domain,
            before=result.before,
            after=result.after,
            ttl=resolved_ttl,
            force_used=force,
            result="success" if applied or dry_run else "noop",
            correlation_id=result.correlation_id,
        )
        if applied and verify and result.verification is VerificationStatus.SKIPPED:
            result.verification = VerificationStatus.ACCEPTED_PENDING_VISIBILITY
        return plan, result

    def plan_delete_a_record(
        self, fqdn: str, *, force: bool, zone: str | None = None
    ) -> tuple[str, int | None, list[DNSRecord], MutationPlan]:
        hostname = self._resolve_hostname_for_zone(fqdn, "dns_delete", zone=zone)
        root_domain = self._resolve_dns_zone(hostname, "dns_delete", zone=zone)
        records, serial = self._zone_state(root_domain)
        matches = [item for item in records if item.name == hostname and item.type == "A"]
        if not matches:
            raise NotFoundAppError("dns_delete", "No A record exists for the hostname.", hostname)
        if len(matches) > 1 and not force:
            raise ConflictAppError("dns_delete", "Multiple A records exist for the hostname.", hostname)
        plan = MutationPlan(
            operation="dns_delete",
            planned_action=PlannedAction.DELETE,
            before={"records": [item.model_dump() for item in matches]},
            after=None,
            requires_force=len(matches) > 1,
            summary=f"Delete {len(matches)} A record(s) for {hostname}.",
        )
        return root_domain, serial, matches, plan

    def delete_a_record(
        self,
        fqdn: str,
        *,
        dry_run: bool,
        force: bool,
        verify: bool,
        zone: str | None = None,
    ) -> tuple[MutationPlan, OperationResult]:
        hostname = self._resolve_hostname_for_zone(fqdn, "dns_delete", zone=zone)
        root_domain, serial, matches, plan = self.plan_delete_a_record(hostname, force=force, zone=zone)
        if not dry_run:
            serial = self._require_serial("dns_delete", root_domain, serial)
            remove = [self._line_index(record) for record in matches]
            self._client.mass_edit_zone(zone=root_domain, serial=serial, remove=remove)
        verification = VerificationStatus.SKIPPED
        if not dry_run and verify:
            verification, _ = self._resolver.verify_a(hostname, None)
            if verification is VerificationStatus.RESOLVED_MATCHES_TARGET:
                verification = VerificationStatus.ACCEPTED_PENDING_VISIBILITY
        result = OperationResult(
            operation="dns_delete",
            mode=OperationMode.DNS_ONLY,
            target=hostname,
            zone=root_domain,
            action="dry-run" if dry_run else "deleted",
            applied=not dry_run,
            verification=verification,
            planned_action=plan.planned_action,
            old_value=", ".join(item.value for item in matches),
            before=plan.before,
            after=plan.after,
            message=plan.summary,
        )
        self._audit.record(
            mode=OperationMode.DNS_ONLY,
            operation=result.action,
            hostname=hostname,
            zone=root_domain,
            before=result.before,
            after=result.after,
            ttl=None,
            force_used=force,
            result="success" if not dry_run else "warning",
            correlation_id=result.correlation_id,
        )
        return plan, result

    def verify_record(self, fqdn: str, expected_ip: str | None = None, zone: str | None = None) -> OperationResult:
        hostname = self._resolve_hostname_for_zone(fqdn, "dns_verify", zone=zone)
        root_domain = self._resolve_dns_zone(hostname, "dns_verify", zone=zone)
        verification, addresses = self._resolver.verify_a(hostname, expected_ip)
        return OperationResult(
            operation="dns_verify",
            mode=OperationMode.DNS_ONLY,
            target=hostname,
            zone=root_domain,
            action="verified",
            applied=False,
            verification=verification,
            new_value=", ".join(addresses) if addresses else None,
            message=f"Resolved addresses for {hostname}: {', '.join(addresses) if addresses else 'none'}.",
        )
