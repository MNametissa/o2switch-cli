from __future__ import annotations

import typer

from o2switch_cli.cli.autocomplete import complete_root_domains, complete_subdomain_terms
from o2switch_cli.cli.helpers import confirm_plan, exit_for_result_warning, run_guarded
from o2switch_cli.cli.interactive_support import paginate_items
from o2switch_cli.cli.ui import TerminalUI

app = typer.Typer(help="Manage hosted cPanel subdomains.", rich_markup_mode="rich")


@app.command("search")
def search_subdomains(
    ctx: typer.Context,
    term: str = typer.Argument(..., autocompletion=complete_subdomain_terms),
    page: int = typer.Option(1, "--page", min=1, help="Result page number."),
    page_size: int = typer.Option(20, "--page-size", min=1, max=500, help="Results per page."),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        with ui.status("Searching hosted subdomains", spinner="dots12"):
            subdomains = app_context.runtime().subdomains.search(term)
        window = paginate_items(subdomains, page=page, page_size=page_size)
        ui.print_subdomains(window.items, window)

    run_guarded(ctx, action)


@app.command("create")
def create_subdomain(
    ctx: typer.Context,
    root: str = typer.Option(..., "--root", autocompletion=complete_root_domains),
    label: str = typer.Option(..., "--label"),
    docroot: str | None = typer.Option(None, "--docroot"),
    ip: str | None = typer.Option(None, "--ip"),
    ttl: int | None = typer.Option(None, "--ttl"),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        with ui.status("Inspecting hosted subdomain state", spinner="dots12"):
            parent, _, _, plan = app_context.runtime().subdomains.plan_create(
                root_domain=root, label=label, docroot=docroot, ip=ip
            )
        if not confirm_plan(app_context, ui, plan, zone=parent):
            ui.print_info("Mutation cancelled.")
            return
        with ui.status("Provisioning hosted subdomain", spinner="aesthetic"):
            result = app_context.runtime().subdomains.create(
                root_domain=root,
                label=label,
                docroot=docroot,
                ip=ip,
                ttl=ttl or app_context.settings.default_ttl,
                dry_run=app_context.dry_run,
                force=app_context.force,
                verify=app_context.verify_after_mutation,
            )
        ui.print_result(result)
        exit_for_result_warning(result)

    run_guarded(ctx, action)


@app.command("delete")
def delete_subdomain(
    ctx: typer.Context,
    fqdn: str = typer.Option(..., "--fqdn", autocompletion=complete_subdomain_terms),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        with ui.status("Inspecting hosted subdomain state", spinner="dots12"):
            zone, _, plan = app_context.runtime().subdomains.plan_delete(fqdn)
        if not confirm_plan(app_context, ui, plan, zone=zone):
            ui.print_info("Mutation cancelled.")
            return
        with ui.status("Deleting hosted subdomain", spinner="aesthetic"):
            result = app_context.runtime().subdomains.delete(fqdn, dry_run=app_context.dry_run)
        ui.print_result(result)

    run_guarded(ctx, action)
