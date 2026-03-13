from __future__ import annotations

from contextlib import contextmanager

from o2switch_cli.cli.context import AppContext
from o2switch_cli.cli.interactive import run_interactive_menu
from o2switch_cli.config.settings import AppSettings
from o2switch_cli.core.models import (
    DomainDescriptor,
    DomainType,
    HostnameSearchResult,
    SearchCategory,
    SubdomainDescriptor,
)


def _app_context() -> AppContext:
    return AppContext(
        settings=AppSettings(),
        output_format="text",
        dry_run=False,
        force=False,
        yes=False,
        verbose=False,
        verify_after_mutation=True,
        allow_prompt=True,
    )


@contextmanager
def _noop_status(*args, **kwargs):
    yield None


def test_interactive_dns_search_skips_backend_lookup_for_blank_term(monkeypatch) -> None:
    class FakeDomains:
        def list_domains(self) -> list[DomainDescriptor]:
            return [DomainDescriptor(domain="ginutech.com", type=DomainType.ADDON)]

    class FakeSubdomains:
        def search(self, term: str) -> list[SubdomainDescriptor]:
            assert term == ""
            return [SubdomainDescriptor(fqdn="app.ginutech.com", label="app", root_domain="ginutech.com")]

    class FakeDNS:
        def search(self, term: str) -> list[HostnameSearchResult]:
            raise AssertionError(f"dns.search should not run for blank interactive input, got {term!r}")

    class FakeRuntime:
        domains = FakeDomains()
        subdomains = FakeSubdomains()
        dns = FakeDNS()

    answers = iter(["DNS: search", "Exit"])
    messages: list[str] = []

    class FakeSelect:
        def ask(self):
            return next(answers)

    monkeypatch.setattr(AppContext, "runtime", lambda self: FakeRuntime())
    monkeypatch.setattr(
        "o2switch_cli.cli.interactive.questionary.select",
        lambda *args, **kwargs: FakeSelect(),
    )
    monkeypatch.setattr("o2switch_cli.cli.interactive.TerminalUI.print_banner", lambda self: None)
    monkeypatch.setattr(
        "o2switch_cli.cli.interactive.TerminalUI.prompt_realtime_search",
        lambda self, *args, **kwargs: "",
    )
    monkeypatch.setattr(
        "o2switch_cli.cli.interactive.TerminalUI.print_info",
        lambda self, message: messages.append(message),
    )
    monkeypatch.setattr("o2switch_cli.cli.interactive.TerminalUI.browse_pages", lambda self, *args, **kwargs: None)
    monkeypatch.setattr("o2switch_cli.cli.interactive.TerminalUI.status", _noop_status)

    run_interactive_menu(_app_context())

    assert messages == ["Enter a hostname, IP, or zone to run a DNS search."]


def test_interactive_dns_search_queries_submitted_term_only(monkeypatch) -> None:
    class FakeDomains:
        def list_domains(self) -> list[DomainDescriptor]:
            return [DomainDescriptor(domain="ginutech.com", type=DomainType.ADDON)]

    class FakeSubdomains:
        def search(self, term: str) -> list[SubdomainDescriptor]:
            assert term == ""
            return [SubdomainDescriptor(fqdn="app.ginutech.com", label="app", root_domain="ginutech.com")]

    calls: list[str] = []

    class FakeDNS:
        def search(self, term: str) -> list[HostnameSearchResult]:
            calls.append(term)
            return [
                HostnameSearchResult(
                    category=SearchCategory.DNS_RECORDS,
                    hostname="name.ginutech.com",
                    record_type="A",
                    value="5.196.30.71",
                    zone="ginutech.com",
                )
            ]

    class FakeRuntime:
        domains = FakeDomains()
        subdomains = FakeSubdomains()
        dns = FakeDNS()

    answers = iter(["DNS: search", "Exit"])
    browsed: list[list[HostnameSearchResult]] = []

    class FakeSelect:
        def ask(self):
            return next(answers)

    monkeypatch.setattr(AppContext, "runtime", lambda self: FakeRuntime())
    monkeypatch.setattr(
        "o2switch_cli.cli.interactive.questionary.select",
        lambda *args, **kwargs: FakeSelect(),
    )
    monkeypatch.setattr("o2switch_cli.cli.interactive.TerminalUI.print_banner", lambda self: None)
    monkeypatch.setattr(
        "o2switch_cli.cli.interactive.TerminalUI.prompt_realtime_search",
        lambda self, *args, **kwargs: "name.ginutech.com",
    )
    monkeypatch.setattr("o2switch_cli.cli.interactive.TerminalUI.print_info", lambda self, message: None)
    monkeypatch.setattr(
        "o2switch_cli.cli.interactive.TerminalUI.browse_pages",
        lambda self, items, **kwargs: browsed.append(list(items)),
    )
    monkeypatch.setattr("o2switch_cli.cli.interactive.TerminalUI.status", _noop_status)

    run_interactive_menu(_app_context())

    assert calls == ["name.ginutech.com"]
    assert [item.hostname for item in browsed[0]] == ["name.ginutech.com"]
