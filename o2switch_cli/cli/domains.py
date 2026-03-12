from __future__ import annotations

import typer

from o2switch_cli.cli.helpers import run_guarded
from o2switch_cli.cli.ui import TerminalUI

app = typer.Typer(help="List and search account domains.", rich_markup_mode="rich")


@app.command("list")
def list_domains(ctx: typer.Context) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        domains = app_context.runtime().domains.list_domains()
        ui.print_domains(domains)

    run_guarded(ctx, action)


@app.command("search")
def search_domains(ctx: typer.Context, term: str) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        domains = app_context.runtime().domains.search(term)
        ui.print_domains(domains)

    run_guarded(ctx, action)
