from __future__ import annotations

import typer

from o2switch_cli.cli.helpers import confirm_plan, exit_for_result_warning, run_guarded
from o2switch_cli.cli.ui import TerminalUI

app = typer.Typer(help="Search, upsert, delete, and verify DNS records.", rich_markup_mode="rich")


@app.command("search")
def search_dns(ctx: typer.Context, term: str) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        results = app_context.runtime().dns.search(term)
        ui.print_hostname_search_results(results)

    run_guarded(ctx, action)


@app.command("upsert")
def upsert_dns(
    ctx: typer.Context,
    host: str = typer.Option(..., "--host"),
    ip: str = typer.Option(..., "--ip"),
    ttl: int | None = typer.Option(None, "--ttl"),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        effective_ttl = ttl or app_context.settings.default_ttl
        zone, _, _, plan = app_context.runtime().dns.plan_upsert_a_record(
            host, ip, effective_ttl, force=app_context.force
        )
        if not confirm_plan(app_context, ui, plan, zone=zone):
            ui.print_info("Mutation cancelled.")
            return
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
def delete_dns(ctx: typer.Context, host: str = typer.Option(..., "--host")) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        zone, _, _, plan = app_context.runtime().dns.plan_delete_a_record(host, force=app_context.force)
        if not confirm_plan(app_context, ui, plan, zone=zone):
            ui.print_info("Mutation cancelled.")
            return
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
    host: str = typer.Option(..., "--host"),
    ip: str | None = typer.Option(None, "--ip"),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        result = app_context.runtime().dns.verify_record(host, ip)
        ui.print_result(result)
        exit_for_result_warning(result)

    run_guarded(ctx, action)
