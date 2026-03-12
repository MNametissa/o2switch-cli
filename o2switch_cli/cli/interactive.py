from __future__ import annotations

import questionary

from o2switch_cli.cli.context import AppContext
from o2switch_cli.cli.ui import TerminalUI


def run_interactive_menu(app_context: AppContext) -> None:
    ui = TerminalUI(app_context.console, app_context.output_format)
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
            ui.print_domains(app_context.runtime().domains.list_domains())
        elif choice == "Domains: search":
            term = questionary.text("Search term").ask() or ""
            ui.print_domains(app_context.runtime().domains.search(term))
        elif choice == "DNS: search":
            term = questionary.text("Search term").ask() or ""
            ui.print_records(app_context.runtime().dns.search(term))
        elif choice == "DNS: upsert A record":
            host = questionary.text("Hostname").ask() or ""
            ip = questionary.text("IPv4 target").ask() or ""
            ttl_text = questionary.text("TTL", default=str(app_context.settings.default_ttl)).ask() or str(
                app_context.settings.default_ttl
            )
            zone, _, _, plan = app_context.runtime().dns.plan_upsert_a_record(
                host, ip, int(ttl_text), force=app_context.force
            )
            ui.print_plan(plan, zone=zone)
            if app_context.yes or ui.confirm("Apply this change?"):
                _, result = app_context.runtime().dns.upsert_a_record(
                    host,
                    ip,
                    int(ttl_text),
                    dry_run=app_context.dry_run,
                    force=app_context.force,
                    verify=app_context.verify_after_mutation,
                )
                ui.print_result(result)
        elif choice == "DNS: delete A record":
            host = questionary.text("Hostname").ask() or ""
            zone, _, _, plan = app_context.runtime().dns.plan_delete_a_record(host, force=app_context.force)
            ui.print_plan(plan, zone=zone)
            if app_context.yes or ui.confirm("Delete this record?"):
                _, result = app_context.runtime().dns.delete_a_record(
                    host,
                    dry_run=app_context.dry_run,
                    force=app_context.force,
                    verify=app_context.verify_after_mutation,
                )
                ui.print_result(result)
        elif choice == "DNS: verify":
            host = questionary.text("Hostname").ask() or ""
            result = app_context.runtime().dns.verify_record(host)
            ui.print_result(result)
        elif choice == "Subdomains: search":
            term = questionary.text("Search term").ask() or ""
            ui.print_subdomains(app_context.runtime().subdomains.search(term))
        elif choice == "Subdomains: create":
            root = questionary.text("Root domain").ask() or ""
            label = questionary.text("Label").ask() or ""
            docroot = questionary.text("Docroot", default=f"/public_html/{label or 'app'}").ask()
            ip = questionary.text("IPv4 target (optional)").ask() or None
            ttl_text = questionary.text("TTL", default=str(app_context.settings.default_ttl)).ask() or str(
                app_context.settings.default_ttl
            )
            zone, _, _, plan = app_context.runtime().subdomains.plan_create(
                root_domain=root, label=label, docroot=docroot, ip=ip
            )
            ui.print_plan(plan, zone=zone)
            if app_context.yes or ui.confirm("Create this hosted subdomain?"):
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
        elif choice == "Subdomains: delete":
            fqdn = questionary.text("Hosted subdomain FQDN").ask() or ""
            zone, _, plan = app_context.runtime().subdomains.plan_delete(fqdn)
            ui.print_plan(plan, zone=zone)
            if app_context.yes or ui.confirm("Delete this hosted subdomain?"):
                result = app_context.runtime().subdomains.delete(fqdn, dry_run=app_context.dry_run)
                ui.print_result(result)
        elif choice == "Config: show":
            from o2switch_cli.config.settings import settings_summary

            ui.print_mapping("Active Configuration", settings_summary(app_context.settings))
        elif choice == "Config: test":
            domains = app_context.runtime().domains.list_domains()
            ui.print_mapping(
                "API Access",
                {
                    "cpanel_host": app_context.settings.cpanel_host,
                    "cpanel_user": app_context.settings.cpanel_user,
                    "reachable_domains": len(domains),
                },
            )
