from __future__ import annotations

from dataclasses import dataclass

import questionary

from o2switch_cli.cli.context import AppContext
from o2switch_cli.cli.helpers import run_guarded_interactive
from o2switch_cli.cli.interactive_support import (
    build_dns_search_suggestions,
    build_domain_suggestions,
    build_hostname_suggestions,
    build_subdomain_suggestions,
    filter_domains,
    filter_hostname_results,
    filter_subdomains,
    paginate_items,
)
from o2switch_cli.cli.ui import TerminalUI
from o2switch_cli.core.models import DomainDescriptor, HostnameSearchResult, SubdomainDescriptor

MIN_PAGE_SIZE = 6
MAX_PAGE_SIZE = 12


@dataclass(slots=True)
class InteractiveDataCache:
    domains: list[DomainDescriptor] | None = None
    subdomains: list[SubdomainDescriptor] | None = None

    def get_domains(self, app_context: AppContext, ui: TerminalUI) -> list[DomainDescriptor]:
        if self.domains is None:
            with ui.status("Syncing domain catalog", spinner="dots12"):
                self.domains = app_context.runtime().domains.list_domains()
        return self.domains

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
        if subdomains:
            self.subdomains = None


def _page_size(ui: TerminalUI) -> int:
    return max(MIN_PAGE_SIZE, min(MAX_PAGE_SIZE, ui.console.size.height - 15))


def _browse_hostname_results(
    ui: TerminalUI,
    results: list[HostnameSearchResult],
    *,
    page_size: int,
    empty_message: str,
) -> None:
    if not results:
        ui.print_info(empty_message)
        return

    all_results = list(results)
    visible_results = list(results)
    filter_term = ""
    page = 1

    while True:
        if not visible_results:
            ui.console.clear()
            ui.print_banner()
            ui.print_info(f'No results matched the filter "{filter_term}".')
        else:
            window = paginate_items(visible_results, page=page, page_size=page_size)
            ui.console.clear()
            ui.print_banner()
            if filter_term:
                ui.print_info(f'Filtered view: "{filter_term}"')
            ui.print_hostname_search_results(window.items, window)
            page = window.page

        choices: list[str] = []
        total_pages = max(1, (len(visible_results) + page_size - 1) // page_size)
        if page > 1:
            choices.append("Previous page")
        if page < total_pages and visible_results:
            choices.append("Next page")
        choices.extend(["First page", "Last page", "Filter results"])
        if filter_term:
            choices.append("Reset filters")
        choices.append("Close results")

        action = questionary.select(
            f"Browse results ({page}/{total_pages})",
            choices=choices,
        ).ask()
        if action == "Previous page":
            page -= 1
        elif action == "Next page":
            page += 1
        elif action == "First page":
            page = 1
        elif action == "Last page":
            page = total_pages
        elif action == "Filter results":
            next_filter = ui.prompt_realtime_search(
                "Filter current results",
                suggestions=build_hostname_suggestions(all_results),
                help_text="Type hosted, dns, hostname, record type, IP, zone, or docroot to narrow the result set",
            )
            if next_filter.strip():
                filter_term = next_filter.strip()
                visible_results = filter_hostname_results(all_results, filter_term)
                page = 1
        elif action == "Reset filters":
            filter_term = ""
            visible_results = list(all_results)
            page = 1
        else:
            return


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
        def action(active_context: AppContext, selected_choice: str = choice) -> None:
            if selected_choice == "Domains: list":
                domains = cache.get_domains(active_context, ui)
                ui.browse_pages(
                    domains,
                    page_size=_page_size(ui),
                    empty_message="No account domains are currently available.",
                    render_page=lambda page_items, window: ui.print_domains(page_items, window),
                )
            elif selected_choice == "Domains: search":
                domains = cache.get_domains(active_context, ui)
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
            elif selected_choice == "DNS: search":
                domains = cache.get_domains(active_context, ui)
                subdomains = cache.get_subdomains(active_context, ui)
                term = ui.prompt_realtime_search(
                    "Search hostnames, IPs, or zones",
                    suggestions=build_dns_search_suggestions(domains, subdomains),
                    help_text="Suggestions update while you type; Enter runs the live DNS search",
                )
                if not term.strip():
                    ui.print_info("Enter a hostname, IP, or zone to run a DNS search.")
                    return
                with ui.status("Searching hosted subdomains and DNS zones", spinner="dots12"):
                    matches = active_context.runtime().dns.search(term)
                _browse_hostname_results(
                    ui,
                    matches,
                    page_size=_page_size(ui),
                    empty_message="No DNS or hosted results matched the search term.",
                )
            elif selected_choice == "DNS: upsert A record":
                host = questionary.text("Hostname or label").ask() or ""
                zone_default = ""
                if "." in host:
                    zone_candidates = active_context.runtime().domains.matching_dns_zones(host)
                    if zone_candidates:
                        zone_default = zone_candidates[0]
                dns_zone = questionary.text("DNS zone", default=zone_default).ask() or None
                ip = questionary.text("IPv4 target").ask() or ""
                ttl_text = questionary.text("TTL", default=str(active_context.settings.default_ttl)).ask() or str(
                    active_context.settings.default_ttl
                )
                with ui.status("Inspecting DNS state", spinner="dots12"):
                    zone, _, _, plan = active_context.runtime().dns.plan_upsert_a_record(
                        host,
                        ip,
                        int(ttl_text),
                        force=active_context.force,
                        zone=dns_zone,
                    )
                ui.print_plan(plan, zone=zone)
                if active_context.yes or ui.confirm("Apply this change?"):
                    with ui.status("Applying DNS mutation", spinner="aesthetic"):
                        _, result = active_context.runtime().dns.upsert_a_record(
                            host,
                            ip,
                            int(ttl_text),
                            dry_run=active_context.dry_run,
                            force=active_context.force,
                            verify=active_context.verify_after_mutation,
                            zone=dns_zone,
                        )
                    ui.print_result(result)
                    cache.invalidate(dns=True)
            elif selected_choice == "DNS: delete A record":
                host = questionary.text("Hostname or label").ask() or ""
                zone_default = ""
                if "." in host:
                    zone_candidates = active_context.runtime().domains.matching_dns_zones(host)
                    if zone_candidates:
                        zone_default = zone_candidates[0]
                dns_zone = questionary.text("DNS zone", default=zone_default).ask() or None
                with ui.status("Inspecting DNS state", spinner="dots12"):
                    zone, _, _, plan = active_context.runtime().dns.plan_delete_a_record(
                        host,
                        force=active_context.force,
                        zone=dns_zone,
                    )
                ui.print_plan(plan, zone=zone)
                if active_context.yes or ui.confirm("Delete this record?"):
                    with ui.status("Deleting DNS record", spinner="aesthetic"):
                        _, result = active_context.runtime().dns.delete_a_record(
                            host,
                            dry_run=active_context.dry_run,
                            force=active_context.force,
                            verify=active_context.verify_after_mutation,
                            zone=dns_zone,
                        )
                    ui.print_result(result)
                    cache.invalidate(dns=True)
            elif selected_choice == "DNS: verify":
                host = questionary.text("Hostname or label").ask() or ""
                zone_default = ""
                if "." in host:
                    zone_candidates = active_context.runtime().domains.matching_dns_zones(host)
                    if zone_candidates:
                        zone_default = zone_candidates[0]
                dns_zone = questionary.text("DNS zone", default=zone_default).ask() or None
                with ui.status("Resolving DNS", spinner="dots12"):
                    result = active_context.runtime().dns.verify_record(host, zone=dns_zone)
                ui.print_result(result)
            elif selected_choice == "Subdomains: search":
                subdomains = cache.get_subdomains(active_context, ui)
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
            elif selected_choice == "Subdomains: create":
                root = questionary.text("Root domain").ask() or ""
                label = questionary.text("Label").ask() or ""
                docroot = questionary.text("Docroot", default=f"/public_html/{label or 'app'}").ask()
                ip = questionary.text("IPv4 target (optional)").ask() or None
                ttl_text = questionary.text("TTL", default=str(active_context.settings.default_ttl)).ask() or str(
                    active_context.settings.default_ttl
                )
                with ui.status("Inspecting hosted subdomain state", spinner="dots12"):
                    zone, _, _, plan = active_context.runtime().subdomains.plan_create(
                        root_domain=root, label=label, docroot=docroot, ip=ip
                    )
                ui.print_plan(plan, zone=zone)
                if active_context.yes or ui.confirm("Create this hosted subdomain?"):
                    with ui.status("Provisioning hosted subdomain", spinner="aesthetic"):
                        result = active_context.runtime().subdomains.create(
                            root_domain=root,
                            label=label,
                            docroot=docroot,
                            ip=ip,
                            ttl=int(ttl_text),
                            dry_run=active_context.dry_run,
                            force=active_context.force,
                            verify=active_context.verify_after_mutation,
                        )
                    ui.print_result(result)
                    cache.invalidate(domains=True, dns=True, subdomains=True)
            elif selected_choice == "Subdomains: delete":
                fqdn = questionary.text("Hosted subdomain FQDN").ask() or ""
                with ui.status("Inspecting hosted subdomain state", spinner="dots12"):
                    zone, _, plan = active_context.runtime().subdomains.plan_delete(fqdn)
                ui.print_plan(plan, zone=zone)
                if active_context.yes or ui.confirm("Delete this hosted subdomain?"):
                    with ui.status("Deleting hosted subdomain", spinner="aesthetic"):
                        result = active_context.runtime().subdomains.delete(fqdn, dry_run=active_context.dry_run)
                    ui.print_result(result)
                    cache.invalidate(domains=True, dns=True, subdomains=True)
            elif selected_choice == "Config: show":
                from o2switch_cli.config.settings import settings_summary

                ui.print_mapping("Active Configuration", settings_summary(active_context.settings))
            elif selected_choice == "Config: test":
                with ui.status("Testing API access", spinner="dots12"):
                    domains = active_context.runtime().domains.list_domains()
                ui.print_mapping(
                    "API Access",
                    {
                        "cpanel_host": active_context.settings.cpanel_host,
                        "cpanel_user": active_context.settings.cpanel_user,
                        "reachable_domains": len(domains),
                    },
                )

        run_guarded_interactive(app_context, action)
