from __future__ import annotations

import typer

from o2switch_cli.cli.helpers import confirm_plan, run_guarded
from o2switch_cli.cli.ui import TerminalUI

app = typer.Typer(help="Manage hosted cPanel subdomains.", rich_markup_mode="rich")


@app.command("search")
def search_subdomains(ctx: typer.Context, term: str) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        subdomains = app_context.runtime().subdomains.search(term)
        ui.print_subdomains(subdomains)

    run_guarded(ctx, action)


@app.command("create")
def create_subdomain(
    ctx: typer.Context,
    root: str = typer.Option(..., "--root"),
    label: str = typer.Option(..., "--label"),
    docroot: str | None = typer.Option(None, "--docroot"),
    ip: str | None = typer.Option(None, "--ip"),
    ttl: int | None = typer.Option(None, "--ttl"),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        parent, _, _, plan = app_context.runtime().subdomains.plan_create(
            root_domain=root, label=label, docroot=docroot, ip=ip
        )
        if not confirm_plan(app_context, ui, plan, zone=parent):
            ui.print_info("Mutation cancelled.")
            return
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

    run_guarded(ctx, action)


@app.command("delete")
def delete_subdomain(ctx: typer.Context, fqdn: str = typer.Option(..., "--fqdn")) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        zone, _, plan = app_context.runtime().subdomains.plan_delete(fqdn)
        if not confirm_plan(app_context, ui, plan, zone=zone):
            ui.print_info("Mutation cancelled.")
            return
        result = app_context.runtime().subdomains.delete(fqdn, dry_run=app_context.dry_run)
        ui.print_result(result)

    run_guarded(ctx, action)
