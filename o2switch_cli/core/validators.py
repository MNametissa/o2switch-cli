from __future__ import annotations

import ipaddress
from pathlib import PurePosixPath

from o2switch_cli.core.errors import NotFoundAppError, ValidationAppError


def normalize_hostname(value: str) -> str:
    hostname = value.strip().lower().rstrip(".")
    if not hostname:
        raise ValidationAppError("hostname", "Hostname cannot be empty.")
    if ".." in hostname:
        raise ValidationAppError("hostname", "Hostname contains an empty segment.", hostname)
    labels = hostname.split(".")
    for label in labels:
        if not label:
            raise ValidationAppError("hostname", "Hostname contains an empty segment.", hostname)
        if label.startswith("-") or label.endswith("-"):
            raise ValidationAppError("hostname", "Hostname labels cannot start or end with '-'.", hostname)
    return hostname


def normalize_label(label: str, reserved_labels: list[str]) -> str:
    value = label.strip().lower()
    if not value:
        raise ValidationAppError("subdomain_create", "Label cannot be empty.")
    if "." in value:
        raise ValidationAppError("subdomain_create", "Label must not contain dots.", value)
    if value.startswith("-") or value.endswith("-"):
        raise ValidationAppError("subdomain_create", "Label cannot start or end with '-'.", value)
    if value in {item.lower() for item in reserved_labels}:
        raise ValidationAppError("subdomain_create", f"'{value}' is a reserved label.", value)
    return value


def validate_ipv4(value: str) -> str:
    try:
        return str(ipaddress.IPv4Address(value.strip()))
    except ipaddress.AddressValueError as exc:
        raise ValidationAppError("dns_upsert", "Target IP must be a valid IPv4 address.", value) from exc


def validate_ttl(value: int | None, default: int) -> int:
    ttl = default if value is None else int(value)
    if ttl < 60 or ttl > 86400:
        raise ValidationAppError("dns_upsert", "TTL must be between 60 and 86400 seconds.", str(ttl))
    return ttl


def normalize_docroot(value: str | None, label: str) -> str:
    path = value or f"/public_html/{label}"
    candidate = PurePosixPath(path)
    if ".." in candidate.parts:
        raise ValidationAppError("subdomain_create", "Docroot cannot contain '..'.", path)
    if not str(candidate).startswith("/"):
        candidate = PurePosixPath("/") / candidate
    return str(candidate)


def select_root_domain(hostname: str, root_domains: list[str], operation: str) -> str:
    normalised = normalize_hostname(hostname)
    candidates = []
    for domain in root_domains:
        root = normalize_hostname(domain)
        if normalised == root or normalised.endswith(f".{root}"):
            candidates.append(root)
    if not candidates:
        raise NotFoundAppError(operation, "No matching root domain was found on the account.", normalised)
    return max(candidates, key=len)


def fqdn_for_label(label: str, root_domain: str) -> str:
    return normalize_hostname(f"{label}.{normalize_hostname(root_domain)}")


def canonical_record_name(name: str, zone: str) -> str:
    candidate = normalize_hostname(name)
    normalised_zone = normalize_hostname(zone)
    if candidate == "@":
        return normalised_zone
    if candidate == normalised_zone or candidate.endswith(f".{normalised_zone}"):
        return candidate
    return f"{candidate}.{normalised_zone}"
