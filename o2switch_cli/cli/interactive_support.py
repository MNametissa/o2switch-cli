from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from typing import Generic, TypeVar

from o2switch_cli.core.models import DomainDescriptor, HostnameSearchResult, SubdomainDescriptor

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class SearchSuggestion:
    value: str
    label: str
    meta: str = ""
    search_blob: str = ""


@dataclass(frozen=True, slots=True)
class PageWindow(Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    start_index: int
    end_index: int


def paginate_items(items: Sequence[T], page: int, page_size: int) -> PageWindow[T]:
    safe_page_size = max(1, page_size)
    total_items = len(items)
    total_pages = max(1, ceil(total_items / safe_page_size))
    safe_page = min(max(1, page), total_pages)
    start_index = (safe_page - 1) * safe_page_size
    end_index = min(start_index + safe_page_size, total_items)
    return PageWindow(
        items=list(items[start_index:end_index]),
        page=safe_page,
        page_size=safe_page_size,
        total_items=total_items,
        total_pages=total_pages,
        start_index=start_index,
        end_index=end_index,
    )


def _needle(term: str) -> str:
    return term.strip().lower()


def _search_blob(parts: list[str | None]) -> str:
    return " ".join(part.strip().lower() for part in parts if part and part.strip())


def filter_domains(domains: Sequence[DomainDescriptor], term: str) -> list[DomainDescriptor]:
    needle = _needle(term)
    if not needle:
        return list(domains)
    return [
        item
        for item in domains
        if needle in _search_blob([item.domain, item.type.value, "dns" if item.has_dns_zone else ""])
    ]


def filter_hostname_results(results: Sequence[HostnameSearchResult], term: str) -> list[HostnameSearchResult]:
    needle = _needle(term)
    if not needle:
        return list(results)
    return [
        item
        for item in results
        if needle
        in _search_blob(
            [
                item.hostname,
                item.record_type,
                item.value,
                item.zone,
                item.docroot,
                item.category.value,
                "hosted" if item.managed_by_cpanel else "dns",
            ]
        )
    ]


def filter_subdomains(subdomains: Sequence[SubdomainDescriptor], term: str) -> list[SubdomainDescriptor]:
    needle = _needle(term)
    if not needle:
        return list(subdomains)
    return [
        item
        for item in subdomains
        if needle in _search_blob([item.fqdn, item.label, item.root_domain, item.docroot])
    ]


def build_domain_suggestions(domains: Sequence[DomainDescriptor]) -> list[SearchSuggestion]:
    return [
        SearchSuggestion(
            value=item.domain,
            label=item.domain,
            meta=item.type.value,
            search_blob=_search_blob([item.domain, item.type.value]),
        )
        for item in domains
    ]


def build_hostname_suggestions(results: Sequence[HostnameSearchResult]) -> list[SearchSuggestion]:
    seen: set[tuple[str, str, str]] = set()
    suggestions: list[SearchSuggestion] = []
    for item in results:
        meta = " · ".join(part for part in [item.category.value, item.record_type, item.value, item.zone] if part)
        key = (item.hostname, meta, item.docroot or "")
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(
            SearchSuggestion(
                value=item.hostname,
                label=item.hostname,
                meta=meta or (item.docroot or ""),
                search_blob=_search_blob(
                    [
                        item.hostname,
                        item.record_type,
                        item.value,
                        item.zone,
                        item.docroot,
                        item.category.value,
                    ]
                ),
            )
        )
    return suggestions


def build_dns_search_suggestions(
    domains: Sequence[DomainDescriptor],
    subdomains: Sequence[SubdomainDescriptor],
) -> list[SearchSuggestion]:
    seen: set[tuple[str, str]] = set()
    suggestions: list[SearchSuggestion] = []

    for item in domains:
        meta = f"domain · {item.type.value}"
        key = (item.domain, meta)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(
            SearchSuggestion(
                value=item.domain,
                label=item.domain,
                meta=meta,
                search_blob=_search_blob([item.domain, item.type.value, "domain"]),
            )
        )

    for item in subdomains:
        meta = f"hosted · {item.root_domain}"
        key = (item.fqdn, meta)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(
            SearchSuggestion(
                value=item.fqdn,
                label=item.fqdn,
                meta=meta,
                search_blob=_search_blob([item.fqdn, item.label, item.root_domain, item.docroot, "hosted"]),
            )
        )

    return suggestions


def build_subdomain_suggestions(subdomains: Sequence[SubdomainDescriptor]) -> list[SearchSuggestion]:
    return [
        SearchSuggestion(
            value=item.fqdn,
            label=item.fqdn,
            meta=item.docroot or item.root_domain,
            search_blob=_search_blob([item.fqdn, item.label, item.root_domain, item.docroot]),
        )
        for item in subdomains
    ]
