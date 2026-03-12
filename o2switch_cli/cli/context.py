from __future__ import annotations

import sys
from dataclasses import dataclass, field

import typer
from rich.console import Console

from o2switch_cli.config.settings import AppSettings
from o2switch_cli.core.audit import AuditService
from o2switch_cli.core.auth import ensure_credentials
from o2switch_cli.core.cpanel_client import CpanelClient
from o2switch_cli.core.dns_service import DNSService
from o2switch_cli.core.domain_service import DomainService
from o2switch_cli.core.errors import CliAppError
from o2switch_cli.core.subdomain_service import SubdomainService
from o2switch_cli.infra.resolver import DNSResolver


@dataclass(slots=True)
class RuntimeServices:
    client: CpanelClient
    domains: DomainService
    dns: DNSService
    subdomains: SubdomainService


@dataclass(slots=True)
class AppContext:
    settings: AppSettings
    output_format: str
    dry_run: bool
    force: bool
    yes: bool
    verbose: bool
    verify_after_mutation: bool
    allow_prompt: bool
    console: Console = field(default_factory=lambda: Console())
    _runtime: RuntimeServices | None = None

    def runtime(self) -> RuntimeServices:
        if self._runtime is None:
            self.settings = ensure_credentials(self.settings, allow_prompt=self.allow_prompt)
            client = CpanelClient.from_settings(self.settings)
            audit = AuditService(
                audit_log_path=self.settings.audit_log_path,
                actor=self.settings.cpanel_user or "system",
            )
            domains = DomainService(client)
            resolver = DNSResolver()
            dns = DNSService(client, domains, resolver, audit, self.settings.reserved_labels)
            subdomains = SubdomainService(
                client,
                domains,
                dns,
                audit,
                self.settings.reserved_labels,
            )
            self._runtime = RuntimeServices(client=client, domains=domains, dns=dns, subdomains=subdomains)
        return self._runtime

    def shutdown(self) -> None:
        if self._runtime is not None:
            self._runtime.client.close()


def build_context(
    *,
    settings: AppSettings,
    json_output: bool,
    dry_run: bool,
    force: bool,
    yes: bool,
    verbose: bool,
    no_verify: bool,
) -> AppContext:
    return AppContext(
        settings=settings,
        output_format="json" if json_output else settings.output_format,
        dry_run=dry_run,
        force=force,
        yes=yes,
        verbose=verbose,
        verify_after_mutation=settings.verify_dns_after_mutation and not no_verify,
        allow_prompt=sys.stdin.isatty() and not json_output,
    )


def get_app_context(ctx: typer.Context) -> AppContext:
    if not isinstance(ctx.obj, AppContext):
        raise RuntimeError("Application context was not initialized.")
    return ctx.obj


def raise_for_error(app_context: AppContext, error: CliAppError) -> None:
    from o2switch_cli.cli.ui import TerminalUI

    TerminalUI(app_context.console, app_context.output_format).print_error(error.to_envelope())
    raise typer.Exit(error.exit_code)
