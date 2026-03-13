from __future__ import annotations

from contextlib import contextmanager

import pytest

from o2switch_cli.cli import autocomplete
from o2switch_cli.core.models import (
    DomainDescriptor,
    DomainType,
    HostnameSearchResult,
    SearchCategory,
    SubdomainDescriptor,
)


class FakeDomains:
    def list_domains(self) -> list[DomainDescriptor]:
        return [
            DomainDescriptor(domain="ginutech.com", type=DomainType.ADDON),
            DomainDescriptor(domain="staging.ginutech.com", type=DomainType.SUBDOMAIN),
        ]

    def search(self, term: str) -> list[DomainDescriptor]:
        needle = term.lower()
        return [item for item in self.list_domains() if needle in item.domain]


class FakeSubdomains:
    def search(self, term: str) -> list[SubdomainDescriptor]:
        rows = [
            SubdomainDescriptor(fqdn="app.ginutech.com", label="app", root_domain="ginutech.com"),
            SubdomainDescriptor(fqdn="api.ginutech.com", label="api", root_domain="ginutech.com"),
        ]
        needle = term.lower()
        return [item for item in rows if needle in item.fqdn]


class FakeDNS:
    def search(self, term: str) -> list[HostnameSearchResult]:
        rows = [
            HostnameSearchResult(
                category=SearchCategory.DNS_RECORDS,
                hostname="_dmarc.ginutech.com",
                record_type="TXT",
                value="v=DMARC1; p=none;",
                zone="ginutech.com",
            ),
            HostnameSearchResult(
                category=SearchCategory.AVAILABLE,
                hostname="free.ginutech.com",
                zone="ginutech.com",
            ),
        ]
        needle = term.lower()
        return [item for item in rows if needle in item.hostname]


class FakeRuntime:
    domains = FakeDomains()
    subdomains = FakeSubdomains()
    dns = FakeDNS()


@contextmanager
def fake_completion_runtime(ctx):
    del ctx
    yield FakeRuntime()


def test_complete_root_domains_filters_and_formats(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autocomplete, "completion_runtime", fake_completion_runtime)
    items = autocomplete.complete_root_domains(None, [], "gin")
    assert items == [("ginutech.com", "addon domain")]


def test_complete_hostname_terms_include_dns_and_hosted_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autocomplete, "completion_runtime", fake_completion_runtime)
    items = autocomplete.complete_hostname_terms(None, [], "_d")
    assert ("_dmarc.ginutech.com", "TXT v=DMARC1; p=none;") in items

    hosted = autocomplete.complete_hostname_terms(None, [], "app")
    assert ("app.ginutech.com", "hosted under ginutech.com") in hosted


def test_complete_subdomain_terms_returns_hosted_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autocomplete, "completion_runtime", fake_completion_runtime)
    items = autocomplete.complete_subdomain_terms(None, [], "api")
    assert items == [("api.ginutech.com", "hosted under ginutech.com")]
