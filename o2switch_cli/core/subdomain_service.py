from __future__ import annotations

from o2switch_cli.core.audit import AuditService
from o2switch_cli.core.cpanel_client import CpanelClient
from o2switch_cli.core.dns_service import DNSService
from o2switch_cli.core.domain_service import DomainService
from o2switch_cli.core.errors import (
    ConflictAppError,
    NotFoundAppError,
    NotSupportedAppError,
    TransportAppError,
)
from o2switch_cli.core.models import (
    DomainType,
    MutationPlan,
    OperationMode,
    OperationResult,
    PlannedAction,
    SubdomainDescriptor,
)
from o2switch_cli.core.validators import (
    fqdn_for_label,
    normalize_docroot,
    normalize_hostname,
    normalize_label,
)


class SubdomainService:
    def __init__(
        self,
        client: CpanelClient,
        domains: DomainService,
        dns: DNSService,
        audit: AuditService,
        reserved_labels: list[str],
    ) -> None:
        self._client = client
        self._domains = domains
        self._dns = dns
        self._audit = audit
        self._reserved_labels = reserved_labels

    def _delete_domain_argument(self, hostname: str, root_domain: str) -> str:
        descriptor = self._domains.get_domain_descriptor(root_domain, "subdomain_delete")
        if descriptor.type is DomainType.ADDON:
            label = hostname[: -(len(root_domain) + 1)]
            return f"{label}_{root_domain}"
        return hostname

    def search(self, term: str) -> list[SubdomainDescriptor]:
        needle = term.strip().lower()
        try:
            payload = self._client.list_subdomains().data or []
        except TransportAppError:
            payload = []
        descriptors: list[SubdomainDescriptor] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            fqdn = normalize_hostname(str(row.get("domain") or row.get("fullsubdomain") or ""))
            if needle and needle not in fqdn:
                continue
            root_domain = normalize_hostname(str(row.get("rootdomain") or fqdn.split(".", 1)[1]))
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

        fallback = []
        for item in self._domains.list_domains():
            if item.type.value != "subdomain":
                continue
            if needle and needle not in item.domain:
                continue
            root_domain = self._domains.resolve_root_domain(item.domain, "subdomains_search")
            fallback.append(
                SubdomainDescriptor(
                    fqdn=item.domain,
                    label=item.domain[: -(len(root_domain) + 1)],
                    root_domain=root_domain,
                    managed_by_cpanel=True,
                )
            )
        return sorted(fallback, key=lambda item: item.fqdn)

    def plan_create(
        self, *, root_domain: str, label: str, docroot: str | None, ip: str | None
    ) -> tuple[str, str, str, MutationPlan]:
        parent = normalize_hostname(root_domain)
        if parent not in self._domains.root_domains():
            raise NotFoundAppError("subdomain_create", "Root domain was not found on the account.", parent)
        safe_label = normalize_label(label, self._reserved_labels)
        fqdn = fqdn_for_label(safe_label, parent)
        existing = [item for item in self.search(safe_label) if item.fqdn == fqdn]
        if existing:
            raise ConflictAppError("subdomain_create", "The hosted subdomain already exists.", fqdn)
        target_docroot = normalize_docroot(docroot, safe_label)
        after = {"fqdn": fqdn, "docroot": target_docroot}
        if ip:
            after["dns_target"] = ip
        plan = MutationPlan(
            operation="subdomain_create",
            planned_action=PlannedAction.CREATE,
            before=None,
            after=after,
            summary=f"Create hosted subdomain {fqdn} with docroot {target_docroot}.",
        )
        return parent, safe_label, target_docroot, plan

    def plan_delete(self, fqdn: str) -> tuple[str, str, MutationPlan]:
        hostname = normalize_hostname(fqdn)
        root_domain = self._domains.resolve_root_domain(hostname, "subdomain_delete")
        label = hostname[: -(len(root_domain) + 1)]
        if not label:
            raise NotFoundAppError("subdomain_delete", "The target is not a hosted subdomain.", hostname)
        existing = [item for item in self.search(hostname) if item.fqdn == hostname]
        if not existing:
            raise NotFoundAppError("subdomain_delete", "The hosted subdomain was not found on the account.", hostname)
        plan = MutationPlan(
            operation="subdomain_delete",
            planned_action=PlannedAction.DELETE,
            before={"fqdn": hostname},
            after=None,
            summary=f"Delete hosted subdomain {hostname}.",
        )
        return root_domain, label, plan

    def create(
        self,
        *,
        root_domain: str,
        label: str,
        docroot: str | None,
        ip: str | None,
        ttl: int,
        dry_run: bool,
        force: bool,
        verify: bool,
    ) -> OperationResult:
        parent, safe_label, target_docroot, plan = self.plan_create(
            root_domain=root_domain, label=label, docroot=docroot, ip=ip
        )
        fqdn = fqdn_for_label(safe_label, parent)
        if not dry_run:
            self._client.add_subdomain(domain=safe_label, rootdomain=parent, directory=target_docroot)
        result = OperationResult(
            operation="subdomain_create",
            mode=OperationMode.HOSTED_DNS if ip else OperationMode.HOSTED_ONLY,
            target=fqdn,
            zone=parent,
            action="dry-run" if dry_run else "created",
            applied=not dry_run,
            message=plan.summary,
            planned_action=plan.planned_action,
            after={"fqdn": fqdn, "docroot": target_docroot},
        )
        if ip:
            _, dns_result = self._dns.upsert_a_record(
                fqdn,
                ip,
                ttl,
                dry_run=dry_run,
                force=force,
                verify=verify,
                mode=OperationMode.HOSTED_DNS,
            )
            result.after = {
                "subdomain": {"fqdn": fqdn, "docroot": target_docroot},
                "dns": dns_result.model_dump(mode="json"),
            }
            result.verification = dns_result.verification
        self._audit.record(
            mode=result.mode,
            operation=result.action,
            hostname=fqdn,
            zone=parent,
            before=None,
            after=result.after,
            ttl=ttl if ip else None,
            force_used=force,
            result="success" if not dry_run else "warning",
            correlation_id=result.correlation_id,
        )
        return result

    def delete(self, fqdn: str, *, dry_run: bool) -> OperationResult:
        hostname = normalize_hostname(fqdn)
        root_domain, label, plan = self.plan_delete(hostname)
        if not dry_run:
            try:
                delete_domain = self._delete_domain_argument(hostname, root_domain)
                self._client.delete_subdomain(domain=delete_domain)
            except TransportAppError as exc:
                if self._looks_like_unsupported_delete(str(exc)):
                    raise NotSupportedAppError(
                        "subdomain_delete",
                        "Hosted subdomain deletion is not supported by the detected cPanel API surface.",
                        hostname,
                    ) from exc
                raise
        result = OperationResult(
            operation="subdomain_delete",
            mode=OperationMode.HOSTED_ONLY,
            target=hostname,
            zone=root_domain,
            action="dry-run" if dry_run else "deleted",
            applied=not dry_run,
            planned_action=plan.planned_action,
            message=plan.summary,
        )
        self._audit.record(
            mode=OperationMode.HOSTED_ONLY,
            operation=result.action,
            hostname=hostname,
            zone=root_domain,
            before={"fqdn": hostname},
            after=None,
            ttl=None,
            force_used=False,
            result="success" if not dry_run else "warning",
            correlation_id=result.correlation_id,
        )
        return result

    @staticmethod
    def _looks_like_unsupported_delete(message: str) -> bool:
        detail = message.lower()
        patterns = (
            "unknown app",
            "unknown module",
            "unknown function",
            "function not found",
            "invalid function",
            "not supported",
        )
        return any(pattern in detail for pattern in patterns)
