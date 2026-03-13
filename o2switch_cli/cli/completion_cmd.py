from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import typer

from o2switch_cli.cli.completion_support import (
    COMMAND_NAMES,
    bash_completion_script,
    default_bash_completion_dir,
    default_bashrc_path,
    install_bash_completion,
    remove_bash_completion,
)
from o2switch_cli.cli.helpers import run_guarded
from o2switch_cli.cli.ui import TerminalUI
from o2switch_cli.core.errors import ValidationAppError

app = typer.Typer(help="Install, remove, and inspect shell completion support.", rich_markup_mode="rich")


class CompletionShell(StrEnum):
    BASH = "bash"


@app.command("show")
def show_completion(
    ctx: typer.Context,
    shell: CompletionShell = typer.Option(CompletionShell.BASH, "--shell", help="Shell to render completion for."),
    command_name: str = typer.Option(
        COMMAND_NAMES[0],
        "--command-name",
        help="Launcher name to bind completion to.",
    ),
) -> None:
    del shell

    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        ui.console.print(bash_completion_script(command_name), end="")

    run_guarded(ctx, action)


@app.command("install")
def install_completion(
    ctx: typer.Context,
    shell: CompletionShell = typer.Option(CompletionShell.BASH, "--shell", help="Shell to install completion for."),
    completion_dir: Path = typer.Option(
        default_bash_completion_dir(),
        "--completion-dir",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Directory where completion files should be written.",
    ),
    bashrc_path: Path = typer.Option(
        default_bashrc_path(),
        "--bashrc-path",
        dir_okay=False,
        file_okay=True,
        resolve_path=True,
        help="Shell rc file to update with the managed completion block.",
    ),
) -> None:
    if shell is not CompletionShell.BASH:
        raise ValidationAppError("completion_install", "Only bash completion is currently supported.", shell.value)

    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        written = install_bash_completion(completion_dir=completion_dir, bashrc_path=bashrc_path)
        ui.print_mapping(
            "Completion Installed",
            {
                "shell": shell.value,
                "completion_dir": str(completion_dir),
                "bashrc_path": str(bashrc_path),
                "commands": ", ".join(COMMAND_NAMES),
                "files": ", ".join(str(path) for path in written),
                "reload": f'source "{bashrc_path}" && hash -r',
            },
        )

    run_guarded(ctx, action)


@app.command("remove")
def remove_completion(
    ctx: typer.Context,
    shell: CompletionShell = typer.Option(CompletionShell.BASH, "--shell", help="Shell to remove completion for."),
    completion_dir: Path = typer.Option(
        default_bash_completion_dir(),
        "--completion-dir",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="Directory where completion files were written.",
    ),
    bashrc_path: Path = typer.Option(
        default_bashrc_path(),
        "--bashrc-path",
        dir_okay=False,
        file_okay=True,
        resolve_path=True,
        help="Shell rc file containing the managed completion block.",
    ),
) -> None:
    if shell is not CompletionShell.BASH:
        raise ValidationAppError("completion_remove", "Only bash completion is currently supported.", shell.value)

    def action(app_context):
        ui = TerminalUI(app_context.console, app_context.output_format)
        removed = remove_bash_completion(completion_dir=completion_dir, bashrc_path=bashrc_path)
        ui.print_mapping(
            "Completion Removed",
            {
                "shell": shell.value,
                "completion_dir": str(completion_dir),
                "bashrc_path": str(bashrc_path),
                "commands": ", ".join(COMMAND_NAMES),
                "files": ", ".join(str(path) for path in removed) if removed else "none",
                "reload": f'source "{bashrc_path}" && hash -r',
            },
        )

    run_guarded(ctx, action)
