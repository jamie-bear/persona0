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
        f"{rollbacks} rollbacks ({100 * rollbacks // total if total else 0}%) | "
        f"total time: {total_ms}ms"
    )

    # Policy outcome details (CP-5)
    _render_policy_outcomes(entries)

    # Macro-cycle observability details
    _render_macro_details(entries)


def _render_policy_outcomes(entries: list) -> None:
    """Render a summary of policy check outcomes if present."""
    policy_entries = [
        e for e in entries if e.get("policy_check_result") or e.get("_policy_check_result")
    ]
    if not policy_entries:
        return

    table = Table(
        title="Policy Check Outcomes",
        box=box.SIMPLE_HEAD,
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Cycle", style="cyan", width=12)
    table.add_column("Passed", width=8)
    table.add_column("Blocked", style="red", width=8)
    table.add_column("Warnings", style="yellow", width=9)
    table.add_column("Block Categories", overflow="fold")

    for i, entry in enumerate(policy_entries, 1):
        result = entry.get("policy_check_result") or entry.get("_policy_check_result", {})
        passed = result.get("passed", True)
        table.add_row(
            str(i),
            entry.get("cycle_type", "?"),
            "[green]YES[/green]" if passed else "[red]NO[/red]",
            str(result.get("blocked", 0)),
            str(result.get("warnings", 0)),
            ", ".join(result.get("block_categories", [])) or "—",
        )

    console.print(table)


def _render_macro_details(entries: list) -> None:
    """Render macro-cycle specific observability data."""
    macro_entries = [e for e in entries if e.get("cycle_type") == "macro"]
    if not macro_entries:
        return

    table = Table(
        title="Macro Cycle Details",
        box=box.SIMPLE_HEAD,
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Reflections", style="green", width=12)
    table.add_column("Beliefs Changed", style="yellow", width=15)
    table.add_column("Goals Active", width=12)
    table.add_column("Abandoned", style="red", width=10)
    table.add_column("Compacted", style="dim", width=12)
    table.add_column("Unmet Drives", overflow="fold")

    for i, entry in enumerate(macro_entries, 1):
        review = entry.get("_macro_goal_review", {})
        compaction = entry.get("_macro_compaction", {})
        unmet = entry.get("_macro_unmet_drives", [])
        accepted = entry.get("_macro_accepted_reflections", [])
        archival = entry.get("_macro_archival_candidates", [])

        compacted_str = "—"
        if compaction and not compaction.get("skipped"):
            compacted_str = f"C:{compaction.get('cooled', 0)} A:{compaction.get('archived', 0)}"

        table.add_row(
            str(i),
            str(len(accepted)),
            str(len(archival)) + " decayed" if archival else "0",
            str(review.get("active_goal_count", "?")),
            str(len(review.get("abandoned_goal_ids", []))),
            compacted_str,
            ", ".join(f"{d['drive']}={d['value']}" for d in unmet) if unmet else "—",
        )

    console.print(table)


def main() -> None:
    if len(sys.argv) < 2:
        console.print("[red]Usage:[/red] python -m src.cli.trace_viewer <log_file>")
        sys.exit(1)
    render_log(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
