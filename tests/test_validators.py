from __future__ import annotations

import pytest

from o2switch_cli.core.errors import NotFoundAppError, ValidationAppError
from o2switch_cli.core.validators import (
    canonical_record_name,
    fqdn_for_label,
    normalize_docroot,
    normalize_hostname,
    normalize_label,
    select_root_domain,
    validate_ipv4,
    validate_ttl,
)


def test_normalize_hostname_trims_and_lowercases() -> None:
    assert normalize_hostname("  Odoo-Staging.Ginutech.com. ") == "odoo-staging.ginutech.com"


def test_normalize_label_rejects_reserved_names() -> None:
    with pytest.raises(ValidationAppError):
        normalize_label("www", ["www"])


def test_validate_ipv4_rejects_ipv6() -> None:
    with pytest.raises(ValidationAppError):
        validate_ipv4("2001:db8::1")


def test_validate_ttl_enforces_range() -> None:
    with pytest.raises(ValidationAppError):
        validate_ttl(30, 300)


def test_select_root_domain_picks_longest_match() -> None:
    assert (
        select_root_domain(
            "api.staging.ginutech.com",
            ["ginutech.com", "staging.ginutech.com"],
            "dns_upsert",
        )
        == "staging.ginutech.com"
    )


def test_select_root_domain_raises_when_missing() -> None:
    with pytest.raises(NotFoundAppError):
        select_root_domain("app.example.com", ["ginutech.com"], "dns_upsert")


def test_fqdn_and_docroot_helpers() -> None:
    assert fqdn_for_label("odoo", "ginutech.com") == "odoo.ginutech.com"
    assert normalize_docroot("public_html/odoo", "odoo") == "/public_html/odoo"
    assert canonical_record_name("odoo", "ginutech.com") == "odoo.ginutech.com"
