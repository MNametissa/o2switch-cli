from __future__ import annotations

from pathlib import Path

import questionary
import typer

from o2switch_cli.cli.helpers import run_guarded
from o2switch_cli.cli.ui import TerminalUI
from o2switch_cli.config.settings import AppSettings, default_audit_log_path, find_env_file, global_config_path, settings_summary, write_env_file
from o2switch_cli.core.errors import ValidationAppError

app = typer.Typer(help="Inspect active configuration and API reachability.", rich_markup_mode="rich")


@app.command("show")
def show_config(ctx: typer.Context) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        summary = settings_summary(app_context.settings)
        summary["config_file"] = find_env_file() or "(none found)"
        ui.print_mapping("Active Configuration", summary)

    run_guarded(ctx, action)


@app.command("path")
def show_path(ctx: typer.Context) -> None:
    """Show configuration file paths."""
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        ui.print_mapping(
            "Config Paths",
            {
                "active": find_env_file() or "(none)",
                "global": str(global_config_path()),
                "local": str(Path(".env").resolve()),
            },
        )

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


@app.command("init")
def init_config(
    ctx: typer.Context,
    path: Path | None = typer.Option(None, "--path", help="Write credentials to this file. Defaults to global config."),
    cpanel_host: str | None = typer.Option(None, "--cpanel-host", help="cPanel host, for example saule.o2switch.net."),
    cpanel_user: str | None = typer.Option(None, "--cpanel-user", help="cPanel username."),
    cpanel_token: str | None = typer.Option(None, "--cpanel-token", help="cPanel API token."),
    default_ttl: int | None = typer.Option(None, "--default-ttl", help="Default TTL to write into the env file."),
    audit_log_path: str | None = typer.Option(
        None,
        "--audit-log-path",
        help="Audit log file path. Defaults to the platform state directory.",
    ),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", help="Fail instead of prompting for missing values."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing env file without confirmation."),
    test_api: bool = typer.Option(False, "--test-api/--no-test-api", help="Test cPanel API access after writing."),
) -> None:
    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        current = app_context.settings
        target = (path or global_config_path()).expanduser().resolve()

        if target.exists() and not force and not non_interactive:
            if not ui.confirm(f"{target} already exists. Overwrite it?"):
                ui.print_info("Setup cancelled.")
                return
        elif target.exists() and not force and non_interactive:
            raise ValidationAppError("config_init", f"{target} already exists. Use --force to overwrite.", str(target))

        host = cpanel_host or current.cpanel_host
        user = cpanel_user or current.cpanel_user
        token = cpanel_token or (current.cpanel_token.get_secret_value() if current.cpanel_token else None)
        ttl = default_ttl if default_ttl is not None else current.default_ttl
        audit_path = (
            audit_log_path
            if audit_log_path is not None
            else current.audit_log_path or default_audit_log_path()
        )

        if not non_interactive:
            host = host or questionary.text("cPanel host", default=current.cpanel_host or "").ask()
            user = user or questionary.text("cPanel user", default=current.cpanel_user or "").ask()
            token = token or questionary.password("cPanel API token").ask()
            ttl_text = questionary.text("Default TTL", default=str(ttl)).ask() or str(ttl)
            try:
                ttl = int(ttl_text)
            except ValueError as exc:
                raise ValidationAppError("config_init", "Default TTL must be an integer.", str(target)) from exc
            audit_path = questionary.text("Audit log path", default=audit_path).ask() or audit_path

        host = host.strip() if host else None
        user = user.strip() if user else None
        token = token.strip() if token else None
        audit_path = (
            audit_path.strip()
            if isinstance(audit_path, str) and audit_path.strip()
            else default_audit_log_path()
        )

        if not host or not user or not token:
            raise ValidationAppError(
                "config_init",
                "cpanel host, user, and token are required.",
                str(target),
            )

        settings = AppSettings(
            cpanel_host=host,
            cpanel_user=user,
            cpanel_token=token,
            port=current.port,
            timeout_seconds=current.timeout_seconds,
            default_ttl=ttl,
            verify_dns_after_mutation=current.verify_dns_after_mutation,
            reserved_labels=current.reserved_labels,
            output_format=current.output_format,
            audit_log_path=audit_path,
        )
        written = write_env_file(target, settings)
        ui.print_mapping(
            "Setup Written",
            {
                "path": str(written),
                "cpanel_host": host,
                "cpanel_user": user,
                "default_ttl": ttl,
                "audit_log_path": audit_path,
            },
        )

        if test_api:
            test_settings = AppSettings(_env_file=str(written))
            app_context.shutdown()
            app_context.settings = test_settings
            app_context._runtime = None
            domains = app_context.runtime().domains.list_domains()
            ui.print_mapping(
                "API Access",
                {
                    "cpanel_host": test_settings.cpanel_host,
                    "cpanel_user": test_settings.cpanel_user,
                    "reachable_domains": len(domains),
                },
            )

    run_guarded(ctx, action)
