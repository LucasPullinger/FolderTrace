from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from fileaudit.database import (
    default_database_path,
    duplicate_groups,
    latest_scan_id,
    save_scan,
)
from fileaudit.hashing import hash_records
from fileaudit.scanner import scan_folder

app = typer.Typer(help="Audit local file collections.", no_args_is_help=True)
console = Console()


# Run FileAudit commands.
@app.callback()
def main() -> None:
    pass


# Scan 'folder' and print a summary of the files found.
@app.command(help="Scan FOLDER and print a summary of the files found.")
def scan(
    folder: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Folder to scan recursively.",
    ),
    database: Path = typer.Option(
        default_database_path(),
        "--database",
        "-d",
        help="SQLite database file used to store the scan.",
    ),
) -> None:
    records = hash_records(scan_folder(folder))
    total_size = sum(record.size for record in records)
    scan_id = save_scan(database, folder, records)

    table = Table(title="Scan complete", show_header=False)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value")
    table.add_row("Scan ID", str(scan_id))
    table.add_row("Scanned", str(folder))
    table.add_row("Files", str(len(records)))
    table.add_row("Total size", _format_size(total_size))
    table.add_row("Database", str(database.expanduser()))
    console.print(table)


# Display exact duplicate files from a saved scan.
@app.command(help="Show exact duplicate files from the latest or selected scan.")
def duplicates(
    database: Path = typer.Option(
        default_database_path(),
        "--database",
        "-d",
        help="SQLite database file to query.",
    ),
    scan_id: int | None = typer.Option(
        None,
        "--scan-id",
        help="Saved scan ID to inspect. Defaults to the latest completed scan.",
    ),
) -> None:
    selected_scan_id = scan_id if scan_id is not None else latest_scan_id(database)
    if selected_scan_id is None:
        raise typer.BadParameter("No completed scans found in this database.")

    groups = duplicate_groups(database, selected_scan_id)
    if not groups:
        console.print(f"No exact duplicates found in scan {selected_scan_id}.")
        return

    console.print(f"[bold]Exact duplicates: scan {selected_scan_id}[/bold]")
    for number, group in enumerate(groups, start=1):
        console.print(f"\n[bold]Duplicate group {number}[/bold]")
        console.print(f"SHA-256: {group.sha256}")
        console.print(f"Copies: {len(group.files)}")
        console.print(f"Duplicate space: {_format_size(group.duplicate_size)}")
        for file in group.files:
            console.print(file.path)


# Format a byte count into a compact, human-readable value.
def _format_size(size: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{size} B"
        value /= 1024
    raise AssertionError("unreachable")


if __name__ == "__main__":
    app()