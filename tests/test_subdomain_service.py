from __future__ import annotations

import pytest

from o2switch_cli.core.audit import AuditService
from o2switch_cli.core.dns_service import DNSService
from o2switch_cli.core.domain_service import DomainService
from o2switch_cli.core.errors import NotFoundAppError, NotSupportedAppError, TransportAppError
from o2switch_cli.core.models import ApiResult, VerificationStatus
from o2switch_cli.core.subdomain_service import SubdomainService


class FakeClient:
    def __init__(
        self,
        hosted: list[dict] | None = None,
        *,
        delete_error: str | None = None,
        domains_payload: dict | None = None,
    ) -> None:
        self.hosted = hosted or []
        self.delete_error = delete_error
        self.domains_payload = domains_payload or {
            "main_domain": "ginutech.com",
            "addon_domains": [],
            "parked_domains": [],
        }
        self.delete_calls: list[dict[str, str]] = []

    def list_domains(self) -> ApiResult:
        return ApiResult(data=self.domains_payload)

    def list_subdomains(self) -> ApiResult:
        return ApiResult(data=self.hosted)

    def delete_subdomain(self, *, domain: str) -> ApiResult:
        if self.delete_error:
            raise TransportAppError("SubDomain::delsubdomain", self.delete_error)
        self.delete_calls.append({"domain": domain})
        return ApiResult(data={"domain": domain})

    def parse_zone(self, zone: str) -> ApiResult:
        return ApiResult(data={"entries": []}, metadata={"serial": 1})

    def mass_edit_zone(self, **kwargs) -> ApiResult:
        return ApiResult(data=kwargs)

    def add_subdomain(self, *, domain: str, rootdomain: str, directory: str) -> ApiResult:
        return ApiResult(data={"domain": domain, "rootdomain": rootdomain, "dir": directory})


class FakeResolver:
    def verify_a(self, hostname: str, expected_ip: str | None = None) -> tuple[VerificationStatus, list[str]]:
        return VerificationStatus.RESOLVED_MATCHES_TARGET, [expected_ip] if expected_ip else []


def build_service(
    *,
    hosted: list[dict] | None = None,
    delete_error: str | None = None,
    domains_payload: dict | None = None,
) -> tuple[FakeClient, SubdomainService]:
    client = FakeClient(hosted=hosted, delete_error=delete_error, domains_payload=domains_payload)
    domains = DomainService(client)  # type: ignore[arg-type]
    dns = DNSService(client, domains, FakeResolver(), AuditService(), ["www", "mail"])  # type: ignore[arg-type]
    return client, SubdomainService(client, domains, dns, AuditService(), ["www", "mail"])


def test_plan_delete_requires_existing_hosted_subdomain() -> None:
    _, service = build_service(hosted=[])
    with pytest.raises(NotFoundAppError):
        service.plan_delete("missing.ginutech.com")


def test_delete_maps_unsupported_endpoint_to_not_supported() -> None:
    _, service = build_service(
        hosted=[{"domain": "app.ginutech.com", "rootdomain": "ginutech.com", "dir": "/public_html/app"}],
        delete_error="Unknown function delsubdomain",
    )
    with pytest.raises(NotSupportedAppError):
        service.delete("app.ginutech.com", dry_run=False)


def test_delete_formats_addon_subdomain_argument_with_underscore() -> None:
    client, service = build_service(
        hosted=[{"domain": "app.blog.example.com", "rootdomain": "blog.example.com", "dir": "/public_html/app"}],
        domains_payload={"main_domain": "ginutech.com", "addon_domains": ["blog.example.com"], "parked_domains": []},
    )
    service.delete("app.blog.example.com", dry_run=False)
    assert client.delete_calls[0]["domain"] == "app_blog.example.com"
