from __future__ import annotations

import json
from typing import Any

import questionary
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from o2switch_cli.core.models import (
    DNSRecord,
    DomainDescriptor,
    ErrorEnvelope,
    HostnameSearchResult,
    MutationPlan,
    OperationResult,
    SubdomainDescriptor,
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

    def _print_json(self, payload: Any) -> None:
        self.console.print_json(json=json.dumps(payload, default=str))

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

    def print_domains(self, domains: list[DomainDescriptor]) -> None:
        if self.output_format == "json":
            self._print_json([item.model_dump(mode="json") for item in domains])
            return
        table = Table(title="Domains", box=box.HEAVY_HEAD, border_style="#ffb000")
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
        self.console.print(table)

    def print_records(self, records: list[DNSRecord]) -> None:
        if self.output_format == "json":
            self._print_json([item.model_dump(mode="json") for item in records])
            return
        table = Table(title="DNS Records", box=box.SIMPLE_HEAVY, border_style="cyan")
        table.add_column("Hostname", style="bold")
        table.add_column("Type")
        table.add_column("Value")
        table.add_column("TTL", justify="right")
        table.add_column("Zone")
        for item in records:
            table.add_row(item.name, item.type, item.value or "-", str(item.ttl or "-"), item.zone)
        self.console.print(table)

    def print_hostname_search_results(self, results: list[HostnameSearchResult]) -> None:
        if self.output_format == "json":
            self._print_json([item.model_dump(mode="json") for item in results])
            return
        table = Table(title="Hostname Search", box=box.SIMPLE_HEAVY, border_style="cyan")
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
        self.console.print(table)

    def print_subdomains(self, subdomains: list[SubdomainDescriptor]) -> None:
        if self.output_format == "json":
            self._print_json([item.model_dump(mode="json") for item in subdomains])
            return
        table = Table(title="Hosted Subdomains", box=box.ROUNDED, border_style="magenta")
        table.add_column("FQDN", style="bold")
        table.add_column("Root Domain")
        table.add_column("Docroot")
        for item in subdomains:
            table.add_row(item.fqdn, item.root_domain, item.docroot or "-")
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

    def print_info(self, message: str) -> None:
        self.console.print(Panel.fit(message, border_style="cyan", box=box.SQUARE))
