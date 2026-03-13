from __future__ import annotations

from o2switch_cli.cli.interactive_support import (
    build_dns_search_suggestions,
    build_hostname_suggestions,
    filter_domains,
    filter_hostname_results,
    paginate_items,
)
from o2switch_cli.core.models import (
    DomainDescriptor,
    DomainType,
    HostnameSearchResult,
    SearchCategory,
    SubdomainDescriptor,
)


def test_paginate_items_clamps_out_of_range_pages() -> None:
    window = paginate_items(["a", "b", "c"], page=9, page_size=2)
    assert window.page == 2
    assert window.total_pages == 2
    assert window.items == ["c"]


def test_filter_domains_matches_domain_and_type() -> None:
    domains = [
        DomainDescriptor(domain="ginutech.com", type=DomainType.MAIN),
        DomainDescriptor(domain="ginutech.net", type=DomainType.PARKED),
    ]
    assert [item.domain for item in filter_domains(domains, "parked")] == ["ginutech.net"]
    assert [item.domain for item in filter_domains(domains, "ginutech")] == ["ginutech.com", "ginutech.net"]


def test_filter_hostname_results_matches_value_and_docroot() -> None:
    results = [
        HostnameSearchResult(
            category=SearchCategory.DNS_RECORDS,
            hostname="odoo.ginutech.com",
            record_type="A",
            value="203.0.113.25",
            zone="ginutech.com",
        ),
        HostnameSearchResult(
            category=SearchCategory.HOSTED_SUBDOMAINS,
            hostname="app.ginutech.com",
            zone="ginutech.com",
            managed_by_cpanel=True,
            docroot="/public_html/app",
        ),
    ]
    by_ip = filter_hostname_results(results, "203.0.113.25")
    by_docroot = filter_hostname_results(results, "/public_html/app")
    assert [item.hostname for item in by_ip] == ["odoo.ginutech.com"]
    assert [item.hostname for item in by_docroot] == ["app.ginutech.com"]


def test_build_hostname_suggestions_deduplicates_repeat_rows() -> None:
    results = [
        HostnameSearchResult(
            category=SearchCategory.DNS_RECORDS,
            hostname="odoo.ginutech.com",
            record_type="A",
            value="203.0.113.25",
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
    suggestions = build_hostname_suggestions(results)
    assert len(suggestions) == 1
    assert suggestions[0].value == "odoo.ginutech.com"


def test_build_dns_search_suggestions_combines_domains_and_subdomains() -> None:
    domains = [
        DomainDescriptor(domain="ginutech.com", type=DomainType.ADDON),
        DomainDescriptor(domain="ginutech.com", type=DomainType.ADDON),
    ]
    subdomains = [
        SubdomainDescriptor(fqdn="app.ginutech.com", label="app", root_domain="ginutech.com"),
        SubdomainDescriptor(fqdn="app.ginutech.com", label="app", root_domain="ginutech.com"),
    ]

    suggestions = build_dns_search_suggestions(domains, subdomains)

    assert [(item.value, item.meta) for item in suggestions] == [
        ("ginutech.com", "domain · addon"),
        ("app.ginutech.com", "hosted · ginutech.com"),
    ]
