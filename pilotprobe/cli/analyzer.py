"""
PilotProbe Headless CLI Analyzer & Exporter
Provides command line diagnostics, offline analysis, session exports, and replays.
"""
import os
import sys
import json
import csv
import click
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ProbeConfig
from store.database import MessageStore
from replay.engine import ReplayEngine


def print_cli_banner():
    """Print a small CLI title."""
    print(f"\033[96m⚛ PilotProbe head-less CLI Diagnostics Tool\033[0m")
    print(f"\033[2m{'═' * 60}\033[0m")


@click.group()
def cli():
    """Headless analysis, session exports, and traffic replay for PilotProbe."""
    pass


@cli.command(name="stats")
@click.option("--db", default=ProbeConfig.DATABASE_PATH, help="Path to SQLite DB file.")
def cmd_stats(db):
    """Show aggregate message and validation statistics."""
    print_cli_banner()
    if not os.path.exists(db):
        click.echo(f"Error: Database file not found at {db}")
        sys.exit(1)

    store = MessageStore(db_path=db)
    stats = store.get_stats()

    click.echo(f"Database File: {click.format_filename(db)}")
    click.echo(f"Total Messages: {stats['total_messages']}")
    click.echo(f"Validation Errors: {stats['validation_errors']}")
    click.echo("\nDistribution by Quantum Paradigm:")
    for sys_type, count in stats["by_system"].items():
        click.echo(f"  - {sys_type:<18}: {count} messages")

    click.echo("\nTop Message Types:")
    for msg_type, count in stats["by_type"].items():
        click.echo(f"  - {msg_type:<20}: {count} messages")


@cli.command(name="export")
@click.option("--db", default=ProbeConfig.DATABASE_PATH, help="Path to SQLite DB file.")
@click.option("--output", required=True, type=click.Path(), help="Output file path (ends in .json or .csv).")
@click.option("--system", help="Filter by system type.")
def cmd_export(db, output, system):
    """Export captured ZMQ message logs to JSON or CSV."""
    print_cli_banner()
    if not os.path.exists(db):
        click.echo(f"Error: Database file not found at {db}")
        sys.exit(1)

    store = MessageStore(db_path=db)
    messages = store.query_messages(system_type=system, limit=1000000)

    if not messages:
        click.echo("No messages found to export.")
        return

    # Export formatting
    formatted = []
    for m in messages:
        ts = datetime.fromtimestamp(m["timestamp"]).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        formatted.append({
            "id": m["id"],
            "timestamp": ts,
            "system_type": m["system_type"],
            "direction": m["direction"],
            "channel": m["channel"],
            "msg_type": m["msg_type"] or "Unknown",
            "task_id": m["task_id"] or "",
            "sn": m["sn"] if m["sn"] is not None else "",
            "is_valid": "Yes" if m["is_valid"] else "No",
            "validation_errors": m["validation_errors"] or "",
            "raw_payload": m["raw_payload"]
        })

    # JSON export
    if output.endswith(".json"):
        with open(output, "w", encoding="utf-8") as f:
            json.dump(formatted, f, indent=2, ensure_ascii=False)
        click.echo(f"Successfully exported {len(formatted)} messages to JSON: {output}")

    # CSV export
    elif output.endswith(".csv"):
        fields = ["id", "timestamp", "system_type", "direction", "channel", "msg_type", "task_id", "sn", "is_valid", "validation_errors", "raw_payload"]
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(formatted)
        click.echo(f"Successfully exported {len(formatted)} messages to CSV: {output}")

    else:
        click.echo("Error: Output file format must be either .json or .csv")
        sys.exit(1)


@cli.command(name="replay")
@click.option("--db", default=ProbeConfig.DATABASE_PATH, help="Path to SQLite DB file.")
@click.option("--system", help="Limit replay to a specific system type (e.g. superconducting).")
@click.option("--task", help="Limit replay to a specific TaskId.")
@click.option("--speed", default=1.0, help="Replay speed multiplier (0.0 for max speed, 1.0 for real-time).")
@click.option("--host", default="localhost", help="Host address of running simulators.")
def cmd_replay(db, system, task, speed, host):
    """Replay recorded ZMQ requests and detect regression/drift."""
    print_cli_banner()
    if not os.path.exists(db):
        click.echo(f"Error: Database file not found at {db}")
        sys.exit(1)

    engine = ReplayEngine(db_path=db)
    click.echo(f"Starting Replay Session (speed multiplier: {speed}x)...")
    
    results = engine.replay_session(system_type=system, task_id=task, speed=speed, target_host=host)

    if not results:
        return

    click.echo(f"\n{click.style('═' * 60, fg='cyan')}")
    click.echo(f"{click.style('REPLAY SUMMARY REPORT', bold=True)}")
    click.echo(f"{click.style('═' * 60, fg='cyan')}")

    total = len(results)
    matches = sum(1 for r in results if r["match"])
    mismatches = total - matches

    for r in results:
        status_str = click.style("MATCH", fg="green", bold=True) if r["match"] else click.style("MISMATCH", fg="red", bold=True)
        click.echo(f"  [{status_str}] ID={r['request_id']} {r['system_type']}: {r['msg_type']} (SN={r['sn']})")
        if not r["match"]:
            click.echo(f"            Details: {r['diff_details']}")

    click.echo(f"\nReplayed: {total} requests")
    click.echo(f"Matches : {click.style(str(matches), fg='green')}")
    click.echo(f"Drifts  : {click.style(str(mismatches), fg='red' if mismatches > 0 else 'green')}")

    if mismatches > 0:
        click.echo(f"\n{click.style('⚠️ Warning: Mismatch detected. Simulators showed state drift or regression.', fg='yellow')}")
        sys.exit(1)
    else:
        click.echo(f"\n{click.style('✅ All replayed requests matches perfectly.', fg='green')}")


if __name__ == "__main__":
    cli()
