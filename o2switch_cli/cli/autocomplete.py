from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import typer

from o2switch_cli.config.settings import AppSettings, load_settings
from o2switch_cli.core.audit import AuditService
from o2switch_cli.core.cpanel_client import CpanelClient
from o2switch_cli.core.dns_service import DNSService
from o2switch_cli.core.domain_service import DomainService
from o2switch_cli.core.models import (
    DomainDescriptor,
    DomainType,
    HostnameSearchResult,
    SearchCategory,
    SubdomainDescriptor,
)
from o2switch_cli.core.subdomain_service import SubdomainService
from o2switch_cli.infra.resolver import DNSResolver

MAX_COMPLETIONS = 40
MIN_NETWORKED_SEARCH = 2

CompletionItem = tuple[str, str]


@dataclass(slots=True)
class CompletionRuntime:
    client: CpanelClient
    domains: DomainService
    dns: DNSService
    subdomains: SubdomainService


def _settings_from_context(ctx: typer.Context | None) -> AppSettings | None:
    try:
        root = ctx.find_root() if ctx is not None else None
        config = root.params.get("config") if root is not None else None
        config_path = config if isinstance(config, Path) else None
        settings = load_settings(config_path)
    except Exception:
        return None
    token = settings.cpanel_token.get_secret_value() if settings.cpanel_token else None
    if not settings.cpanel_host or not settings.cpanel_user or not token:
        return None
    return settings


@contextmanager
def completion_runtime(ctx: typer.Context | None) -> Iterator[CompletionRuntime | None]:
    settings = _settings_from_context(ctx)
    if settings is None:
        yield None
        return

    client: CpanelClient | None = None
    try:
        client = CpanelClient.from_settings(settings)
        audit = AuditService(
            audit_log_path=settings.audit_log_path,
            actor=settings.cpanel_user or "completion",
        )
        domains = DomainService(client)
        dns = DNSService(client, domains, DNSResolver(), audit, settings.reserved_labels)
        subdomains = SubdomainService(client, domains, dns, audit, settings.reserved_labels)
        yield CompletionRuntime(client=client, domains=domains, dns=dns, subdomains=subdomains)
    except Exception:
        yield None
    finally:
        if client is not None:
            client.close()


def _match_candidates(candidates: list[CompletionItem], incomplete: str) -> list[CompletionItem]:
    query = incomplete.strip().lower()
    prefix_matches: list[CompletionItem] = []
    contains_matches: list[CompletionItem] = []
    seen: set[str] = set()

    for value, help_text in candidates:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        if not query or key.startswith(query):
            prefix_matches.append((value, help_text))
        elif query in key:
            contains_matches.append((value, help_text))

    return (prefix_matches + contains_matches)[:MAX_COMPLETIONS]


def _domain_items(domains: list[DomainDescriptor]) -> list[CompletionItem]:
    return [(item.domain, f"{item.type.value} domain") for item in domains]


def _subdomain_items(subdomains: list[SubdomainDescriptor]) -> list[CompletionItem]:
    return [
        (
            item.fqdn,
            f"hosted under {item.root_domain}",
        )
        for item in subdomains
    ]


def _hostname_items(results: list[HostnameSearchResult]) -> list[CompletionItem]:
    items: list[CompletionItem] = []
    for item in results:
        if item.category is SearchCategory.DNS_RECORDS:
            detail = f"{item.record_type or 'record'} {item.value or ''}".strip()
        elif item.category is SearchCategory.HOSTED_SUBDOMAINS:
            detail = "hosted subdomain"
        else:
            detail = "available hostname"
        items.append((item.hostname, detail))
    return items


def complete_domain_terms(ctx: typer.Context, args: list[str], incomplete: str) -> list[CompletionItem]:
    del args
    with completion_runtime(ctx) as runtime:
        if runtime is None:
            return []
        return _match_candidates(_domain_items(runtime.domains.list_domains()), incomplete)


def complete_root_domains(ctx: typer.Context, args: list[str], incomplete: str) -> list[CompletionItem]:
    del args
    with completion_runtime(ctx) as runtime:
        if runtime is None:
            return []
        roots = [
            item
            for item in runtime.domains.list_domains()
            if item.eligible_for_subdomain_creation and item.type is not DomainType.SUBDOMAIN
        ]
        return _match_candidates(_domain_items(roots), incomplete)


def complete_subdomain_terms(ctx: typer.Context, args: list[str], incomplete: str) -> list[CompletionItem]:
    del args
    with completion_runtime(ctx) as runtime:
        if runtime is None:
            return []
        return _match_candidates(_subdomain_items(runtime.subdomains.search(incomplete)), incomplete)


def complete_hostname_terms(ctx: typer.Context, args: list[str], incomplete: str) -> list[CompletionItem]:
    del args
    with completion_runtime(ctx) as runtime:
        if runtime is None:
            return []

        candidates: list[CompletionItem] = []
        domain_matches = runtime.domains.search(incomplete) if incomplete else runtime.domains.list_domains()
        subdomain_matches = runtime.subdomains.search(incomplete)
        candidates.extend(_domain_items(domain_matches))
        candidates.extend(_subdomain_items(subdomain_matches))

        should_query_dns = incomplete and (
            len(incomplete.strip()) >= MIN_NETWORKED_SEARCH or "." in incomplete or incomplete.startswith("_")
        )
        if should_query_dns:
            candidates.extend(_hostname_items(runtime.dns.search(incomplete)))

        return _match_candidates(candidates, incomplete)
