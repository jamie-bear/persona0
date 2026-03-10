"""
CLI trace viewer for cycle logs.

Usage:
    python -m src.cli.trace_viewer <log_file>

Renders the cycle log as a readable rich table showing:
  - cycle_type, timestamp, modules executed, field deltas, before/after hash
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box


console = Console()


def _short_hash(h: str) -> str:
    return h[:12] if h else ""


def _format_delta(delta: dict) -> str:
    if not delta:
        return "[dim]—[/dim]"
    lines = []
    for key, change in delta.items():
        if isinstance(change, dict) and "before" in change and "after" in change:
            lines.append(f"{key}: {change['before']!r} → {change['after']!r}")
        else:
            lines.append(f"{key}: {change!r}")
    return "\n".join(lines[:5])  # cap at 5 lines for readability


def _format_policy(summary: dict) -> str:
    if not summary:
        return "[dim]—[/dim]"

    blocked = int(summary.get("blocked", 0))
    warnings = int(summary.get("warnings", 0))
    if blocked > 0:
        cats = ", ".join(summary.get("block_categories", [])[:3])
        return f"[red]blocked={blocked}[/red]\n[dim]{cats}[/dim]"
    if warnings > 0:
        return f"[yellow]warnings={warnings}[/yellow]"
    return "[green]pass[/green]"


def render_log(log_path: Path) -> None:
    if not log_path.exists():
        console.print(f"[red]File not found:[/red] {log_path}")
        sys.exit(1)

    entries = []
    with log_path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                console.print(f"[yellow]Line {i}: parse error:[/yellow] {exc}")

    if not entries:
        console.print("[yellow]No entries found.[/yellow]")
        return

    table = Table(
        title=f"Cycle Log — {log_path.name} ({len(entries)} entries)",
        box=box.SIMPLE_HEAD,
        show_lines=True,
        expand=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Timestamp", style="dim", width=26)
    table.add_column("Steps", style="green", width=10)
    table.add_column("Writes", style="yellow", width=7)
    table.add_column("Before hash", style="dim", width=14)
    table.add_column("After hash", style="dim", width=14)
    table.add_column("Status", width=16)
    table.add_column("Policy", width=24)
    table.add_column("Delta (top 5 fields)", overflow="fold")

    for i, entry in enumerate(entries, 1):
        rollback = entry.get("rollback", False)
        status_str = (
            f"[red]ROLLBACK\n{entry.get('rollback_reason', '')[:40]}[/red]"
            if rollback
            else "[green]OK[/green]"
        )
        table.add_row(
            str(i),
            entry.get("cycle_type", "?"),
            entry.get("timestamp", "")[:25],
            str(len(entry.get("modules_executed", []))),
            str(entry.get("write_count", 0)),
            _short_hash(entry.get("before_state_hash", "")),
            _short_hash(entry.get("after_state_hash", "")),
            status_str,
            _format_policy(entry.get("policy_check_result") or {}),
            _format_delta(entry.get("delta", {})),
        )

    console.print(table)

    # Summary line
    total = len(entries)
    rollbacks = sum(1 for e in entries if e.get("rollback"))
    total_ms = sum(e.get("duration_ms", 0) for e in entries)
    console.print(
        f"[bold]Summary:[/bold] {total} cycles | "
        f"{rollbacks} rollbacks ({100*rollbacks//total if total else 0}%) | "
        f"total time: {total_ms}ms"
    )


def main() -> None:
    if len(sys.argv) < 2:
        console.print("[red]Usage:[/red] python -m src.cli.trace_viewer <log_file>")
        sys.exit(1)
    render_log(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
