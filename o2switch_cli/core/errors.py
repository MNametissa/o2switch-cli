from __future__ import annotations

from dataclasses import dataclass

from o2switch_cli.core.models import ErrorClass, ErrorEnvelope

EXIT_CODE_BY_CLASS = {
    ErrorClass.VALIDATION: 2,
    ErrorClass.AUTH: 3,
    ErrorClass.PERMISSION: 3,
    ErrorClass.NOT_FOUND: 4,
    ErrorClass.CONFLICT: 5,
    ErrorClass.TRANSPORT: 6,
    ErrorClass.NOT_SUPPORTED: 6,
    ErrorClass.VERIFICATION: 7,
}


@dataclass(slots=True)
class CliAppError(Exception):
    error_class: ErrorClass
    operation: str
    message: str
    target: str | None = None
    safe_next_step: str = "Review the input and retry."

    @property
    def exit_code(self) -> int:
        return EXIT_CODE_BY_CLASS[self.error_class]

    def to_envelope(self) -> ErrorEnvelope:
        return ErrorEnvelope(
            error_class=self.error_class,
            operation=self.operation,
            target=self.target,
            message=self.message,
            safe_next_step=self.safe_next_step,
        )


class ValidationAppError(CliAppError):
    def __init__(self, operation: str, message: str, target: str | None = None) -> None:
        super().__init__(ErrorClass.VALIDATION, operation, message, target, "Fix the input and retry.")


class AuthAppError(CliAppError):
    def __init__(self, operation: str, message: str = "Missing or invalid cPanel credentials.") -> None:
        super().__init__(
            ErrorClass.AUTH,
            operation,
            message,
            safe_next_step="Set O2SWITCH_CLI_CPANEL_HOST, O2SWITCH_CLI_CPANEL_USER, and O2SWITCH_CLI_CPANEL_TOKEN.",
        )


class PermissionAppError(CliAppError):
    def __init__(self, operation: str, target: str | None = None) -> None:
        super().__init__(
            ErrorClass.PERMISSION,
            operation,
            "cPanel denied the requested operation.",
            target,
            "Verify token scope and account permissions, then retry.",
        )


class NotFoundAppError(CliAppError):
    def __init__(self, operation: str, message: str, target: str | None = None) -> None:
        super().__init__(
            ErrorClass.NOT_FOUND,
            operation,
            message,
            target,
            "Verify the target domain or hostname exists on the account and retry.",
        )


class ConflictAppError(CliAppError):
    def __init__(self, operation: str, message: str, target: str | None = None) -> None:
        super().__init__(
            ErrorClass.CONFLICT,
            operation,
            message,
            target,
            "Review the conflicting records and rerun with --force only if the target is confirmed.",
        )


class TransportAppError(CliAppError):
    def __init__(self, operation: str, message: str) -> None:
        super().__init__(
            ErrorClass.TRANSPORT,
            operation,
            message,
            safe_next_step="Check network reachability, endpoint availability, and API response shape.",
        )


class VerificationAppError(CliAppError):
    def __init__(self, operation: str, target: str, message: str) -> None:
        super().__init__(
            ErrorClass.VERIFICATION,
            operation,
            message,
            target,
            "The mutation was accepted, but public DNS visibility may still be propagating.",
        )


class NotSupportedAppError(CliAppError):
    def __init__(self, operation: str, message: str, target: str | None = None) -> None:
        super().__init__(
            ErrorClass.NOT_SUPPORTED,
            operation,
            message,
            target,
            "Use the supported hosted workflow or verify endpoint support on the target cPanel account.",
        )
