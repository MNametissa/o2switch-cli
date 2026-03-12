from __future__ import annotations

from dataclasses import dataclass

import questionary

from o2switch_cli.cli.context import AppContext
from o2switch_cli.cli.interactive_support import (
    build_domain_suggestions,
    build_hostname_suggestions,
    build_subdomain_suggestions,
    filter_domains,
    filter_hostname_results,
    filter_subdomains,
)
from o2switch_cli.cli.ui import TerminalUI
from o2switch_cli.core.models import DomainDescriptor, HostnameSearchResult, SubdomainDescriptor

MIN_PAGE_SIZE = 6
MAX_PAGE_SIZE = 12


@dataclass(slots=True)
class InteractiveDataCache:
    domains: list[DomainDescriptor] | None = None
    dns_index: list[HostnameSearchResult] | None = None
    subdomains: list[SubdomainDescriptor] | None = None

    def get_domains(self, app_context: AppContext, ui: TerminalUI) -> list[DomainDescriptor]:
        if self.domains is None:
            with ui.status("Syncing domain catalog", spinner="dots12"):
                self.domains = app_context.runtime().domains.list_domains()
        return self.domains

    def get_dns_index(self, app_context: AppContext, ui: TerminalUI) -> list[HostnameSearchResult]:
        if self.dns_index is None:
            with ui.status("Scanning hosted subdomains and DNS zones", spinner="dots12"):
                self.dns_index = app_context.runtime().dns.search("")
        return self.dns_index

    def get_subdomains(self, app_context: AppContext, ui: TerminalUI) -> list[SubdomainDescriptor]:
        if self.subdomains is None:
            with ui.status("Syncing hosted subdomains", spinner="dots12"):
                self.subdomains = app_context.runtime().subdomains.search("")
        return self.subdomains

    def invalidate(
        self,
        *,
        domains: bool = False,
        dns: bool = False,
        subdomains: bool = False,
    ) -> None:
        if domains:
            self.domains = None
        if dns:
            self.dns_index = None
        if subdomains:
            self.subdomains = None


def _page_size(ui: TerminalUI) -> int:
    return max(MIN_PAGE_SIZE, min(MAX_PAGE_SIZE, ui.console.size.height - 15))


def run_interactive_menu(app_context: AppContext) -> None:
    ui = TerminalUI(app_context.console, app_context.output_format)
    cache = InteractiveDataCache()
    ui.print_banner()
    while True:
        choice = questionary.select(
            "Choose an operation",
            choices=[
                "Domains: list",
                "Domains: search",
                "DNS: search",
                "DNS: upsert A record",
                "DNS: delete A record",
                "DNS: verify",
                "Subdomains: search",
                "Subdomains: create",
                "Subdomains: delete",
                "Config: show",
                "Config: test",
                "Exit",
            ],
        ).ask()

        if choice == "Exit" or choice is None:
            return
        if choice == "Domains: list":
            domains = cache.get_domains(app_context, ui)
            ui.browse_pages(
                domains,
                page_size=_page_size(ui),
                empty_message="No account domains are currently available.",
                render_page=lambda page_items, window: ui.print_domains(page_items, window),
            )
        elif choice == "Domains: search":
            domains = cache.get_domains(app_context, ui)
            term = ui.prompt_realtime_search(
                "Search domains",
                suggestions=build_domain_suggestions(domains),
                help_text="Realtime domain matches update while you type",
            )
            matches = filter_domains(domains, term)
            ui.browse_pages(
                matches,
                page_size=_page_size(ui),
                empty_message="No domains matched the search term.",
                render_page=lambda page_items, window: ui.print_domains(page_items, window),
            )
        elif choice == "DNS: search":
            results = cache.get_dns_index(app_context, ui)
            term = ui.prompt_realtime_search(
                "Search hostnames, IPs, or zones",
                suggestions=build_hostname_suggestions(results),
                help_text="Realtime DNS and hosted matches update while you type",
            )
            matches = filter_hostname_results(results, term)
            if not matches and term.strip():
                with ui.status("Checking live hostname availability", spinner="earth"):
                    matches = app_context.runtime().dns.search(term)
            ui.browse_pages(
                matches,
                page_size=_page_size(ui),
                empty_message="No DNS or hosted results matched the search term.",
                render_page=lambda page_items, window: ui.print_hostname_search_results(page_items, window),
            )
        elif choice == "DNS: upsert A record":
            host = questionary.text("Hostname").ask() or ""
            ip = questionary.text("IPv4 target").ask() or ""
            ttl_text = questionary.text("TTL", default=str(app_context.settings.default_ttl)).ask() or str(
                app_context.settings.default_ttl
            )
            with ui.status("Inspecting DNS state", spinner="dots12"):
                zone, _, _, plan = app_context.runtime().dns.plan_upsert_a_record(
                    host, ip, int(ttl_text), force=app_context.force
                )
            ui.print_plan(plan, zone=zone)
            if app_context.yes or ui.confirm("Apply this change?"):
                with ui.status("Applying DNS mutation", spinner="aesthetic"):
                    _, result = app_context.runtime().dns.upsert_a_record(
                        host,
                        ip,
                        int(ttl_text),
                        dry_run=app_context.dry_run,
                        force=app_context.force,
                        verify=app_context.verify_after_mutation,
                    )
                ui.print_result(result)
                cache.invalidate(dns=True)
        elif choice == "DNS: delete A record":
            host = questionary.text("Hostname").ask() or ""
            with ui.status("Inspecting DNS state", spinner="dots12"):
                zone, _, _, plan = app_context.runtime().dns.plan_delete_a_record(host, force=app_context.force)
            ui.print_plan(plan, zone=zone)
            if app_context.yes or ui.confirm("Delete this record?"):
                with ui.status("Deleting DNS record", spinner="aesthetic"):
                    _, result = app_context.runtime().dns.delete_a_record(
                        host,
                        dry_run=app_context.dry_run,
                        force=app_context.force,
                        verify=app_context.verify_after_mutation,
                    )
                ui.print_result(result)
                cache.invalidate(dns=True)
        elif choice == "DNS: verify":
            host = questionary.text("Hostname").ask() or ""
            with ui.status("Resolving DNS", spinner="dots12"):
                result = app_context.runtime().dns.verify_record(host)
            ui.print_result(result)
        elif choice == "Subdomains: search":
            subdomains = cache.get_subdomains(app_context, ui)
            term = ui.prompt_realtime_search(
                "Search hosted subdomains",
                suggestions=build_subdomain_suggestions(subdomains),
                help_text="Realtime hosted subdomain matches update while you type",
            )
            matches = filter_subdomains(subdomains, term)
            ui.browse_pages(
                matches,
                page_size=_page_size(ui),
                empty_message="No hosted subdomains matched the search term.",
                render_page=lambda page_items, window: ui.print_subdomains(page_items, window),
            )
        elif choice == "Subdomains: create":
            root = questionary.text("Root domain").ask() or ""
            label = questionary.text("Label").ask() or ""
            docroot = questionary.text("Docroot", default=f"/public_html/{label or 'app'}").ask()
            ip = questionary.text("IPv4 target (optional)").ask() or None
            ttl_text = questionary.text("TTL", default=str(app_context.settings.default_ttl)).ask() or str(
                app_context.settings.default_ttl
            )
            with ui.status("Inspecting hosted subdomain state", spinner="dots12"):
                zone, _, _, plan = app_context.runtime().subdomains.plan_create(
                    root_domain=root, label=label, docroot=docroot, ip=ip
                )
            ui.print_plan(plan, zone=zone)
            if app_context.yes or ui.confirm("Create this hosted subdomain?"):
                with ui.status("Provisioning hosted subdomain", spinner="aesthetic"):
                    result = app_context.runtime().subdomains.create(
                        root_domain=root,
                        label=label,
                        docroot=docroot,
                        ip=ip,
                        ttl=int(ttl_text),
                        dry_run=app_context.dry_run,
                        force=app_context.force,
                        verify=app_context.verify_after_mutation,
                    )
                ui.print_result(result)
                cache.invalidate(domains=True, dns=True, subdomains=True)
        elif choice == "Subdomains: delete":
            fqdn = questionary.text("Hosted subdomain FQDN").ask() or ""
            with ui.status("Inspecting hosted subdomain state", spinner="dots12"):
                zone, _, plan = app_context.runtime().subdomains.plan_delete(fqdn)
            ui.print_plan(plan, zone=zone)
            if app_context.yes or ui.confirm("Delete this hosted subdomain?"):
                with ui.status("Deleting hosted subdomain", spinner="aesthetic"):
                    result = app_context.runtime().subdomains.delete(fqdn, dry_run=app_context.dry_run)
                ui.print_result(result)
                cache.invalidate(domains=True, dns=True, subdomains=True)
        elif choice == "Config: show":
            from o2switch_cli.config.settings import settings_summary

            ui.print_mapping("Active Configuration", settings_summary(app_context.settings))
        elif choice == "Config: test":
            with ui.status("Testing API access", spinner="dots12"):
                domains = app_context.runtime().domains.list_domains()
            ui.print_mapping(
                "API Access",
                {
                    "cpanel_host": app_context.settings.cpanel_host,
                    "cpanel_user": app_context.settings.cpanel_user,
                    "reachable_domains": len(domains),
                },
            )
