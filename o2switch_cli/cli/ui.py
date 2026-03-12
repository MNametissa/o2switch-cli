from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from contextlib import nullcontext
from typing import Any, TypeVar

import questionary
from prompt_toolkit import prompt
from prompt_toolkit.application.current import get_app_or_none
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from o2switch_cli.cli.interactive_support import PageWindow, SearchSuggestion, paginate_items
from o2switch_cli.core.models import (
    DNSRecord,
    DomainDescriptor,
    ErrorEnvelope,
    HostnameSearchResult,
    MutationPlan,
    OperationResult,
    SubdomainDescriptor,
)

T = TypeVar("T")


class SearchSuggestionCompleter(Completer):
    def __init__(self, suggestions: Sequence[SearchSuggestion], *, limit: int = 8) -> None:
        self._suggestions = list(suggestions)
        self._limit = limit

    def match_count(self, query: str) -> int:
        needle = query.strip().lower()
        if not needle:
            return len(self._suggestions)
        return sum(1 for item in self._suggestions if needle in (item.search_blob or item.label.lower()))

    def get_completions(self, document, complete_event):
        query = document.text_before_cursor
        needle = query.strip().lower()
        matches = [
            item
            for item in self._suggestions
            if not needle or needle in (item.search_blob or item.label.lower())
        ]
        matches.sort(
            key=lambda item: (
                0
                if not needle or item.label.lower().startswith(needle) or item.value.lower().startswith(needle)
                else 1,
                len(item.label),
                item.label,
            )
        )
        start_position = -len(query)
        for item in matches[: self._limit]:
            yield Completion(
                item.value,
                start_position=start_position,
                display=item.label,
                display_meta=item.meta or "",
            )


class TerminalUI:
    def __init__(self, console: Console | None = None, output_format: str = "text") -> None:
        self.console = console or Console()
        self.output_format = output_format

    def print_banner(self) -> None:
        title = Text("O2SWITCH CLI", style="bold #ffb000")
        body = (
            "[bold #ffd166]DNS-first cPanel operator console[/]\n"
            "[dim]Domains, hosted subdomains, and zone changes without blind writes.[/dim]"
        )
        self.console.print(
            Panel.fit(
                body,
                title=title,
                border_style="#ffb000",
                box=box.DOUBLE_EDGE,
                padding=(1, 2),
            )
        )

    def status(self, message: str, *, spinner: str = "dots12"):
        if self.output_format == "json":
            return nullcontext()
        return self.console.status(f"[bold #ffb000]{message}[/]", spinner=spinner, spinner_style="#ffb000")

    def _print_json(self, payload: Any) -> None:
        self.console.print_json(json=json.dumps(payload, default=str))

    @staticmethod
    def _page_caption(page_window: PageWindow[Any] | None) -> str | None:
        if page_window is None or page_window.total_items <= page_window.page_size:
            return None
        start = page_window.start_index + 1 if page_window.total_items else 0
        return (
            f"Page {page_window.page}/{page_window.total_pages} · "
            f"showing {start}-{page_window.end_index} of {page_window.total_items}"
        )

    def print_error(self, envelope: ErrorEnvelope) -> None:
        if self.output_format == "json":
            self._print_json(envelope.model_dump(mode="json"))
            return
        content = (
            f"[bold red]{envelope.message}[/]\n"
            f"[dim]operation[/] {envelope.operation}\n"
            f"[dim]target[/] {envelope.target or '-'}\n"
            f"[dim]next[/] {envelope.safe_next_step}"
        )
        self.console.print(Panel(content, title="Failure", border_style="red", box=box.DOUBLE))

    def _build_domains_table(
        self, domains: Sequence[DomainDescriptor], page_window: PageWindow[DomainDescriptor] | None = None
    ) -> Table:
        table = Table(title="Domains", box=box.HEAVY_HEAD, border_style="#ffb000")
        table.caption = self._page_caption(page_window)
        table.add_column("Domain", style="bold")
        table.add_column("Type")
        table.add_column("Hosted Create", justify="center")
        table.add_column("DNS Zone", justify="center")
        for item in domains:
            table.add_row(
                item.domain,
                item.type.value,
                "yes" if item.eligible_for_subdomain_creation else "no",
                "yes" if item.has_dns_zone else "no",
            )
        return table

    def print_domains(
        self, domains: list[DomainDescriptor], page_window: PageWindow[DomainDescriptor] | None = None
    ) -> None:
        if self.output_format == "json":
            self._print_json([item.model_dump(mode="json") for item in domains])
            return
        table = self._build_domains_table(domains, page_window)
        self.console.print(table)

    def _build_records_table(
        self,
        records: Sequence[DNSRecord],
        page_window: PageWindow[DNSRecord] | None = None,
    ) -> Table:
        table = Table(title="DNS Records", box=box.SIMPLE_HEAVY, border_style="cyan")
        table.caption = self._page_caption(page_window)
        table.add_column("Hostname", style="bold")
        table.add_column("Type")
        table.add_column("Value")
        table.add_column("TTL", justify="right")
        table.add_column("Zone")
        for item in records:
            table.add_row(item.name, item.type, item.value or "-", str(item.ttl or "-"), item.zone)
        return table

    def print_records(self, records: list[DNSRecord], page_window: PageWindow[DNSRecord] | None = None) -> None:
        if self.output_format == "json":
            self._print_json([item.model_dump(mode="json") for item in records])
            return
        table = self._build_records_table(records, page_window)
        self.console.print(table)

    def _build_hostname_search_table(
        self, results: Sequence[HostnameSearchResult], page_window: PageWindow[HostnameSearchResult] | None = None
    ) -> Table:
        table = Table(title="Hostname Search", box=box.SIMPLE_HEAVY, border_style="cyan")
        table.caption = self._page_caption(page_window)
        table.add_column("Category", style="bold")
        table.add_column("Hostname")
        table.add_column("Type")
        table.add_column("Value")
        table.add_column("Zone")
        table.add_column("Hosted")
        for item in results:
            table.add_row(
                item.category.value,
                item.hostname,
                item.record_type or "-",
                item.value or item.docroot or "-",
                item.zone or "-",
                "yes" if item.managed_by_cpanel else "no",
            )
        return table

    def print_hostname_search_results(
        self, results: list[HostnameSearchResult], page_window: PageWindow[HostnameSearchResult] | None = None
    ) -> None:
        if self.output_format == "json":
            self._print_json([item.model_dump(mode="json") for item in results])
            return
        table = self._build_hostname_search_table(results, page_window)
        self.console.print(table)

    def _build_subdomains_table(
        self, subdomains: Sequence[SubdomainDescriptor], page_window: PageWindow[SubdomainDescriptor] | None = None
    ) -> Table:
        table = Table(title="Hosted Subdomains", box=box.ROUNDED, border_style="magenta")
        table.caption = self._page_caption(page_window)
        table.add_column("FQDN", style="bold")
        table.add_column("Root Domain")
        table.add_column("Docroot")
        for item in subdomains:
            table.add_row(item.fqdn, item.root_domain, item.docroot or "-")
        return table

    def print_subdomains(
        self, subdomains: list[SubdomainDescriptor], page_window: PageWindow[SubdomainDescriptor] | None = None
    ) -> None:
        if self.output_format == "json":
            self._print_json([item.model_dump(mode="json") for item in subdomains])
            return
        table = self._build_subdomains_table(subdomains, page_window)
        self.console.print(table)

    def print_mapping(self, title: str, payload: dict[str, Any]) -> None:
        if self.output_format == "json":
            self._print_json(payload)
            return
        table = Table(title=title, box=box.MINIMAL_DOUBLE_HEAD, border_style="#ffb000")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        for key, value in payload.items():
            table.add_row(key, json.dumps(value) if isinstance(value, (dict, list)) else str(value))
        self.console.print(table)

    def print_plan(self, plan: MutationPlan, zone: str | None = None) -> None:
        if self.output_format == "json":
            payload = plan.model_dump(mode="json")
            if zone:
                payload["zone"] = zone
            self._print_json(payload)
            return
        lines = [f"[bold]action[/] {plan.planned_action.value}", f"[bold]summary[/] {plan.summary}"]
        if zone:
            lines.append(f"[bold]zone[/] {zone}")
        if plan.before:
            lines.append(f"[bold]before[/] {json.dumps(plan.before, default=str)}")
        if plan.after:
            lines.append(f"[bold]after[/] {json.dumps(plan.after, default=str)}")
        self.console.print(Panel("\n".join(lines), title="Planned Change", border_style="yellow", box=box.DOUBLE_EDGE))

    def print_result(self, result: OperationResult) -> None:
        if self.output_format == "json":
            self._print_json(result.model_dump(mode="json"))
            return
        style = "green" if result.action not in {"dry-run", "no-op"} else "cyan"
        body = (
            f"[bold]operation[/] {result.operation}\n"
            f"[bold]target[/] {result.target}\n"
            f"[bold]zone[/] {result.zone or '-'}\n"
            f"[bold]action[/] {result.action}\n"
            f"[bold]verification[/] {result.verification.value}\n"
            f"[bold]message[/] {result.message}\n"
            f"[dim]correlation[/] {result.correlation_id}"
        )
        self.console.print(Panel(body, title="Result", border_style=style, box=box.DOUBLE))

    def confirm(self, prompt: str) -> bool:
        return bool(questionary.confirm(prompt, default=False).ask())

    def prompt_realtime_search(
        self,
        prompt_text: str,
        *,
        suggestions: Sequence[SearchSuggestion],
        help_text: str,
    ) -> str:
        if self.output_format == "json" or not suggestions:
            return (questionary.text(prompt_text).ask() or "").strip()
        completer = SearchSuggestionCompleter(suggestions)

        def toolbar() -> HTML:
            app = get_app_or_none()
            query = app.current_buffer.text if app else ""
            count = completer.match_count(query)
            return HTML(
                "<style fg='ansibrightblack'>"
                f"{help_text} · {count} live matches · Enter keeps free text"
                "</style>"
            )

        return (
            prompt(
                f"{prompt_text}: ",
                completer=completer,
                complete_while_typing=True,
                complete_in_thread=True,
                mouse_support=True,
                reserve_space_for_menu=min(10, max(4, len(suggestions))),
                bottom_toolbar=toolbar,
            )
            .strip()
        )

    def browse_pages(
        self,
        items: Sequence[T],
        *,
        page_size: int,
        empty_message: str,
        render_page: Callable[[list[T], PageWindow[T]], None],
    ) -> None:
        if not items:
            self.print_info(empty_message)
            return
        page = 1
        while True:
            window = paginate_items(items, page=page, page_size=page_size)
            self.console.clear()
            self.print_banner()
            render_page(window.items, window)
            if window.total_pages <= 1:
                return
            choices: list[str] = []
            if window.page > 1:
                choices.append("Previous page")
            if window.page < window.total_pages:
                choices.append("Next page")
            choices.extend(["First page", "Last page", "Close results"])
            action = questionary.select(
                f"Browse results ({window.page}/{window.total_pages})",
                choices=choices,
            ).ask()
            if action == "Previous page":
                page -= 1
            elif action == "Next page":
                page += 1
            elif action == "First page":
                page = 1
            elif action == "Last page":
                page = window.total_pages
            else:
                return

    def print_info(self, message: str) -> None:
        self.console.print(Panel.fit(message, border_style="cyan", box=box.SQUARE))
