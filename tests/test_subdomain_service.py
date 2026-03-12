from __future__ import annotations

import pytest

from o2switch_cli.core.audit import AuditService
from o2switch_cli.core.dns_service import DNSService
from o2switch_cli.core.domain_service import DomainService
from o2switch_cli.core.errors import NotFoundAppError, NotSupportedAppError, TransportAppError
from o2switch_cli.core.models import ApiResult, VerificationStatus
from o2switch_cli.core.subdomain_service import SubdomainService


class FakeClient:
    def __init__(self, hosted: list[dict] | None = None, *, delete_error: str | None = None) -> None:
        self.hosted = hosted or []
        self.delete_error = delete_error

    def list_domains(self) -> ApiResult:
        return ApiResult(data={"main_domain": "ginutech.com", "addon_domains": [], "parked_domains": []})

    def list_subdomains(self) -> ApiResult:
        return ApiResult(data=self.hosted)

    def delete_subdomain(self, *, domain: str, rootdomain: str) -> ApiResult:
        if self.delete_error:
            raise TransportAppError("SubDomain::delsubdomain", self.delete_error)
        return ApiResult(data={"domain": domain, "rootdomain": rootdomain})

    def parse_zone(self, zone: str) -> ApiResult:
        return ApiResult(data={"entries": []}, metadata={"serial": 1})

    def mass_edit_zone(self, **kwargs) -> ApiResult:
        return ApiResult(data=kwargs)

    def add_subdomain(self, *, domain: str, rootdomain: str, directory: str) -> ApiResult:
        return ApiResult(data={"domain": domain, "rootdomain": rootdomain, "dir": directory})


class FakeResolver:
    def verify_a(self, hostname: str, expected_ip: str | None = None) -> tuple[VerificationStatus, list[str]]:
        return VerificationStatus.RESOLVED_MATCHES_TARGET, [expected_ip] if expected_ip else []


def build_service(*, hosted: list[dict] | None = None, delete_error: str | None = None) -> SubdomainService:
    client = FakeClient(hosted=hosted, delete_error=delete_error)
    domains = DomainService(client)  # type: ignore[arg-type]
    dns = DNSService(client, domains, FakeResolver(), AuditService(), ["www", "mail"])  # type: ignore[arg-type]
    return SubdomainService(client, domains, dns, AuditService(), ["www", "mail"])


def test_plan_delete_requires_existing_hosted_subdomain() -> None:
    service = build_service(hosted=[])
    with pytest.raises(NotFoundAppError):
        service.plan_delete("missing.ginutech.com")


def test_delete_maps_unsupported_endpoint_to_not_supported() -> None:
    service = build_service(
        hosted=[{"domain": "app.ginutech.com", "rootdomain": "ginutech.com", "dir": "/public_html/app"}],
        delete_error="Unknown function delsubdomain",
    )
    with pytest.raises(NotSupportedAppError):
        service.delete("app.ginutech.com", dry_run=False)
