from __future__ import annotations

import sys
from pathlib import Path

import typer

from o2switch_cli.cli.config_cmd import app as config_app
from o2switch_cli.cli.context import build_context
from o2switch_cli.cli.dns import app as dns_app
from o2switch_cli.cli.domains import app as domains_app
from o2switch_cli.cli.helpers import run_guarded
from o2switch_cli.cli.interactive import run_interactive_menu
from o2switch_cli.cli.subdomains import app as subdomains_app
from o2switch_cli.config.settings import load_settings

app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=False,
    rich_markup_mode="rich",
    help="Interactive cPanel DNS and hosted subdomain operator.",
)

app.add_typer(domains_app, name="domains", help="List and search account domains.")
app.add_typer(dns_app, name="dns", help="Inspect and mutate DNS records.")
app.add_typer(subdomains_app, name="subdomains", help="Manage hosted cPanel subdomains.")
app.add_typer(config_app, name="config", help="Inspect configuration and API access.")


@app.callback()
def main(
    ctx: typer.Context,
    config: Path | None = typer.Option(None, "--config", dir_okay=False, readable=True),
    json_output: bool = typer.Option(False, "--json"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force"),
    yes: bool = typer.Option(False, "--yes"),
    verbose: bool = typer.Option(False, "--verbose"),
    no_verify: bool = typer.Option(False, "--no-verify"),
) -> None:
    settings = load_settings(config)
    app_context = build_context(
        settings=settings,
        json_output=json_output,
        dry_run=dry_run,
        force=force,
        yes=yes,
        verbose=verbose,
        no_verify=no_verify,
    )
    ctx.obj = app_context
    ctx.call_on_close(app_context.shutdown)

    if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
        if sys.stdin.isatty():
            run_guarded(ctx, lambda active_context: run_interactive_menu(active_context))
            raise typer.Exit()
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("interactive")
def interactive(ctx: typer.Context) -> None:
    run_guarded(ctx, run_interactive_menu)


def run() -> None:
    app()
