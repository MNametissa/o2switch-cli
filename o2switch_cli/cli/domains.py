from __future__ import annotations

import typer

from o2switch_cli.cli.autocomplete import complete_domain_terms
from o2switch_cli.cli.helpers import run_guarded
from o2switch_cli.cli.interactive_support import paginate_items
from o2switch_cli.cli.ui import TerminalUI

app = typer.Typer(help="List and search account domains.", rich_markup_mode="rich")


@app.command("list")
def list_domains(
    ctx: typer.Context,
    page: int = typer.Option(1, "--page", min=1, help="Result page number."),
    page_size: int = typer.Option(20, "--page-size", min=1, max=500, help="Results per page."),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        with ui.status("Loading account domains", spinner="dots12"):
            domains = app_context.runtime().domains.list_domains()
        window = paginate_items(domains, page=page, page_size=page_size)
        ui.print_domains(window.items, window)

    run_guarded(ctx, action)


@app.command("search")
def search_domains(
    ctx: typer.Context,
    term: str = typer.Argument(..., autocompletion=complete_domain_terms),
    page: int = typer.Option(1, "--page", min=1, help="Result page number."),
    page_size: int = typer.Option(20, "--page-size", min=1, max=500, help="Results per page."),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        with ui.status("Searching account domains", spinner="dots12"):
            domains = app_context.runtime().domains.search(term)
        window = paginate_items(domains, page=page, page_size=page_size)
        ui.print_domains(window.items, window)

    run_guarded(ctx, action)
