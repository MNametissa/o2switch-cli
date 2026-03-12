from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from o2switch_cli.core.models import AuditEvent, OperationMode


class AuditService:
    def __init__(self, audit_log_path: str | None = None, actor: str = "system") -> None:
        self._path = Path(audit_log_path).expanduser() if audit_log_path else None
        self._actor = actor

    def record(
        self,
        *,
        mode: OperationMode,
        operation: str,
        hostname: str,
        zone: str | None,
        before: dict | None,
        after: dict | None,
        ttl: int | None,
        force_used: bool,
        result: str,
        correlation_id: str,
    ) -> AuditEvent:
        event = AuditEvent(
            timestamp=datetime.now(UTC).isoformat(),
            actor=self._actor,
            mode=mode,
            operation=operation,
            hostname=hostname,
            zone=zone,
            before=before,
            after=after,
            ttl=ttl,
            force_used=force_used,
            result=result,
            correlation_id=correlation_id,
        )
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.model_dump(mode="json")) + "\n")
        return event
