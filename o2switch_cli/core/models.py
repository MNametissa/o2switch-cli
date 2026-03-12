from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DomainType(StrEnum):
    MAIN = "main"
    ADDON = "addon"
    PARKED = "parked"
    SUBDOMAIN = "subdomain"
    UNKNOWN = "unknown"


class PlannedAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NOOP = "no-op"
    REFUSE = "refuse"


class OperationMode(StrEnum):
    DNS_ONLY = "dns-only"
    HOSTED_DNS = "hosted+dns"
    HOSTED_ONLY = "hosted-only"


class VerificationStatus(StrEnum):
    SKIPPED = "skipped"
    ACCEPTED_PENDING_VISIBILITY = "accepted_pending_visibility"
    RESOLVED_MATCHES_TARGET = "resolved_matches_target"
    RESOLVED_MISMATCH = "resolved_mismatch"
    LOOKUP_FAILED = "lookup_failed"


class ErrorClass(StrEnum):
    VALIDATION = "validation"
    AUTH = "auth"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    TRANSPORT = "transport"
    VERIFICATION = "verification"
    NOT_SUPPORTED = "not_supported"


class DomainDescriptor(BaseModel):
    domain: str
    type: DomainType
    eligible_for_subdomain_creation: bool = True
    has_dns_zone: bool = True


class DNSRecord(BaseModel):
    name: str
    type: str
    value: str = ""
    ttl: int | None = None
    zone: str
    record_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SubdomainDescriptor(BaseModel):
    fqdn: str
    label: str
    root_domain: str
    docroot: str | None = None
    managed_by_cpanel: bool = True


class MutationPlan(BaseModel):
    operation: str
    planned_action: PlannedAction
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    requires_force: bool = False
    requires_confirmation: bool = True
    summary: str


class OperationResult(BaseModel):
    operation: str
    mode: OperationMode
    target: str
    zone: str | None = None
    action: str
    applied: bool
    verification: VerificationStatus = VerificationStatus.SKIPPED
    message: str
    planned_action: PlannedAction | None = None
    old_value: str | None = None
    new_value: str | None = None
    ttl: int | None = None
    warnings: list[str] = Field(default_factory=list)
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))


class ErrorEnvelope(BaseModel):
    error_class: ErrorClass
    operation: str
    target: str | None = None
    message: str
    safe_next_step: str


class AuditEvent(BaseModel):
    timestamp: str
    actor: str
    mode: OperationMode
    operation: str
    hostname: str
    zone: str | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    ttl: int | None = None
    force_used: bool = False
    result: str
    correlation_id: str


class ApiResult(BaseModel):
    data: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
