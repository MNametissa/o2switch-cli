from __future__ import annotations

import typer

from o2switch_cli.cli.helpers import run_guarded
from o2switch_cli.cli.ui import TerminalUI
from o2switch_cli.config.settings import settings_summary

app = typer.Typer(help="Inspect active configuration and API reachability.", rich_markup_mode="rich")


@app.command("show")
def show_config(ctx: typer.Context) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        ui.print_mapping("Active Configuration", settings_summary(app_context.settings))

    run_guarded(ctx, action)


@app.command("test")
def test_config(ctx: typer.Context) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        domains = app_context.runtime().domains.list_domains()
        ui.print_mapping(
            "API Access",
            {
                "cpanel_host": app_context.settings.cpanel_host,
                "cpanel_user": app_context.settings.cpanel_user,
                "reachable_domains": len(domains),
            },
        )

    run_guarded(ctx, action)
