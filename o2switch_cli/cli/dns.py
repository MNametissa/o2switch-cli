from __future__ import annotations

import typer

from o2switch_cli.cli.autocomplete import complete_hostname_terms
from o2switch_cli.cli.helpers import confirm_plan, exit_for_result_warning, run_guarded
from o2switch_cli.cli.interactive_support import paginate_items
from o2switch_cli.cli.ui import TerminalUI

app = typer.Typer(help="Search, upsert, delete, and verify DNS records.", rich_markup_mode="rich")


@app.command("search")
def search_dns(
    ctx: typer.Context,
    term: str = typer.Argument(..., autocompletion=complete_hostname_terms),
    page: int = typer.Option(1, "--page", min=1, help="Result page number."),
    page_size: int = typer.Option(20, "--page-size", min=1, max=500, help="Results per page."),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        with ui.status("Searching hosted and DNS indexes", spinner="dots12"):
            results = app_context.runtime().dns.search(term)
        window = paginate_items(results, page=page, page_size=page_size)
        ui.print_hostname_search_results(window.items, window)

    run_guarded(ctx, action)


@app.command("upsert")
def upsert_dns(
    ctx: typer.Context,
    host: str = typer.Option(..., "--host", autocompletion=complete_hostname_terms),
    ip: str = typer.Option(..., "--ip"),
    ttl: int | None = typer.Option(None, "--ttl"),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        effective_ttl = ttl or app_context.settings.default_ttl
        with ui.status("Inspecting DNS state", spinner="dots12"):
            zone, _, _, plan = app_context.runtime().dns.plan_upsert_a_record(
                host, ip, effective_ttl, force=app_context.force
            )
        if not confirm_plan(app_context, ui, plan, zone=zone):
            ui.print_info("Mutation cancelled.")
            return
        with ui.status("Applying DNS mutation", spinner="aesthetic"):
            _, result = app_context.runtime().dns.upsert_a_record(
                host,
                ip,
                effective_ttl,
                dry_run=app_context.dry_run,
                force=app_context.force,
                verify=app_context.verify_after_mutation,
            )
        ui.print_result(result)
        exit_for_result_warning(result)

    run_guarded(ctx, action)


@app.command("delete")
def delete_dns(
    ctx: typer.Context,
    host: str = typer.Option(..., "--host", autocompletion=complete_hostname_terms),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        with ui.status("Inspecting DNS state", spinner="dots12"):
            zone, _, _, plan = app_context.runtime().dns.plan_delete_a_record(host, force=app_context.force)
        if not confirm_plan(app_context, ui, plan, zone=zone):
            ui.print_info("Mutation cancelled.")
            return
        with ui.status("Deleting DNS record", spinner="aesthetic"):
            _, result = app_context.runtime().dns.delete_a_record(
                host,
                dry_run=app_context.dry_run,
                force=app_context.force,
                verify=app_context.verify_after_mutation,
            )
        ui.print_result(result)
        exit_for_result_warning(result)

    run_guarded(ctx, action)


@app.command("verify")
def verify_dns(
    ctx: typer.Context,
    host: str = typer.Option(..., "--host", autocompletion=complete_hostname_terms),
    ip: str | None = typer.Option(None, "--ip"),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        with ui.status("Resolving DNS", spinner="dots12"):
            result = app_context.runtime().dns.verify_record(host, ip)
        ui.print_result(result)
        exit_for_result_warning(result)

    run_guarded(ctx, action)
