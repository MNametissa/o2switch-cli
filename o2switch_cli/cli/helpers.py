from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import typer

from o2switch_cli.cli.context import AppContext, get_app_context, raise_for_error
from o2switch_cli.cli.ui import TerminalUI
from o2switch_cli.core.errors import CliAppError, TransportAppError
from o2switch_cli.core.models import MutationPlan, OperationResult, PlannedAction, VerificationStatus

T = TypeVar("T")


def run_guarded(ctx: typer.Context, action: Callable[[AppContext], T]) -> T:
    app_context = get_app_context(ctx)
    try:
        return action(app_context)
    except CliAppError as error:
        raise_for_error(app_context, error)
    except typer.Exit:
        raise
    except Exception as error:  # pragma: no cover
        raise_for_error(app_context, TransportAppError("runtime", str(error)))
    raise RuntimeError("unreachable")


def confirm_plan(app_context: AppContext, ui: TerminalUI, plan: MutationPlan, *, zone: str | None = None) -> bool:
    if ui.output_format != "json":
        ui.print_plan(plan, zone=zone)
    if app_context.dry_run or app_context.yes or plan.planned_action is PlannedAction.NOOP:
        return True
    return ui.confirm("Apply this change?")


def exit_for_result_warning(result: OperationResult) -> None:
    warning_statuses = {
        VerificationStatus.ACCEPTED_PENDING_VISIBILITY,
        VerificationStatus.RESOLVED_MISMATCH,
        VerificationStatus.LOOKUP_FAILED,
    }
    if result.verification in warning_statuses:
        raise typer.Exit(code=7)
