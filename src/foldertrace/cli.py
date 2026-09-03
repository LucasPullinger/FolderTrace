from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from foldertrace.database import (
    archives_for_scan,
    compare_scans,
    default_database_path,
    duplicate_groups,
    latest_scan_id,
    latest_files_for_root,
    save_scan,
    saved_scans,
)
from foldertrace.hashing import hash_records_incrementally
from foldertrace.scanner import scan_folder
from foldertrace.versions import possible_version_groups
from foldertrace.database import files_for_scan
from foldertrace.exporting import export_scan

app = typer.Typer(help="Audit local file collections.", no_args_is_help=True)
console = Console()


# Run FolderTrace commands.
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
    scanned_records = scan_folder(folder)
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), console=console
    ) as progress:
        task = progress.add_task("Hashing files", total=len(scanned_records))
        hashing = hash_records_incrementally(
            scanned_records,
            latest_files_for_root(database, folder),
            lambda: progress.advance(task),
        )
    records = hashing.records
    total_size = sum(record.size for record in records)
    scan_id = save_scan(database, folder, records)

    table = Table(title="Scan complete", show_header=False)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value")
    table.add_row("Scan ID", str(scan_id))
    table.add_row("Scanned", str(folder))
    table.add_row("Files", str(len(records)))
    table.add_row("Hashes reused", str(hashing.reused))
    table.add_row("Hashes calculated", str(hashing.calculated))
    table.add_row("Total size", _format_size(total_size))
    table.add_row("Database", str(database.expanduser()))
    console.print(table)


# Compare two saved scans and summarise their differences.
@app.command(help="Compare two saved scans.")
def changes(
    from_scan: int = typer.Option(..., "--from", help="Earlier scan ID."),
    to_scan: int = typer.Option(..., "--to", help="Later scan ID."),
    details: bool = typer.Option(False, "--details", help="List paths in each category."),
    database: Path = typer.Option(
        default_database_path(),
        "--database",
        "-d",
        help="SQLite database file to query.",
    ),
) -> None:
    try:
        comparison = compare_scans(database, from_scan, to_scan)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    console.print(f"[bold]Scan changes: {from_scan} → {to_scan}[/bold]")
    table = Table(show_header=False)
    table.add_column("Category", style="bold cyan")
    table.add_column("Files", justify="right")
    table.add_row("Added", str(len(comparison.added)))
    table.add_row("Removed", str(len(comparison.removed)))
    table.add_row("Changed", str(len(comparison.changed)))
    table.add_row("Unchanged", str(len(comparison.unchanged)))
    console.print(table)

    if details:
        _print_change_paths("Added", comparison.added)
        _print_change_paths("Removed", comparison.removed)
        _print_change_paths("Changed", comparison.changed)


# List saved scans with their IDs, timestamps, and root folders.
@app.command(help="List saved scans.")
def scans(
    database: Path = typer.Option(
        default_database_path(),
        "--database",
        "-d",
        help="SQLite database file to query.",
    ),
) -> None:
    scan_records = saved_scans(database)
    if not scan_records:
        console.print("No saved scans found.")
        return

    table = Table(title="Saved scans")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Started")
    table.add_column("Completed")
    table.add_column("Folder", overflow="fold")
    for scan_record in scan_records:
        table.add_row(
            str(scan_record.id),
            _format_datetime(scan_record.started_at),
            _format_datetime(scan_record.completed_at),
            scan_record.root_path,
        )
    console.print(table)


# List inspected archives from the latest or selected scan.
@app.command(help="Show a one-screen summary of the latest or selected scan.")
def summary(
    database: Path = typer.Option(default_database_path(), "--database", "-d"),
    scan_id: int | None = typer.Option(None, "--scan-id"),
) -> None:
    selected_scan_id = scan_id if scan_id is not None else latest_scan_id(database)
    if selected_scan_id is None:
        raise typer.BadParameter("No completed scans found in this database.")
    scan_record = next(scan for scan in saved_scans(database) if scan.id == selected_scan_id)
    files = files_for_scan(database, selected_scan_id)
    archive_rows = archives_for_scan(database, selected_scan_id)
    duplicates = duplicate_groups(database, selected_scan_id)
    versions = possible_version_groups(files)
    table = Table(title=f"Scan summary: {selected_scan_id}", show_header=False)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value")
    table.add_row("Folder", scan_record.root_path)
    table.add_row("Files", str(len(files)))
    table.add_row("Total size", _format_size(sum(file.size for file in files)))
    table.add_row("Archives", str(len(archive_rows)))
    table.add_row("Duplicate groups", str(len(duplicates)))
    table.add_row("Duplicate space", _format_size(sum(group.duplicate_size for group in duplicates)))
    table.add_row("Possible version groups", str(len(versions)))
    console.print(table)


# List inspected archives from the latest or selected scan.
@app.command(help="List inspected archives from the latest or selected scan.")
def archives(
    database: Path = typer.Option(default_database_path(), "--database", "-d"),
    scan_id: int | None = typer.Option(None, "--scan-id"),
) -> None:
    selected_scan_id = scan_id if scan_id is not None else latest_scan_id(database)
    if selected_scan_id is None:
        raise typer.BadParameter("No completed scans found in this database.")
    rows = archives_for_scan(database, selected_scan_id)
    if not rows:
        console.print(f"No supported archives found in scan {selected_scan_id}.")
        return
    table = Table(title=f"Archives: scan {selected_scan_id}")
    table.add_column("Archive", overflow="fold")
    table.add_column("Type")
    table.add_column("Files", justify="right")
    table.add_column("Uncompressed", justify="right")
    table.add_column("Status")
    for file, archive in rows:
        table.add_row(file.path, archive.archive_type, str(archive.file_count), _format_size(archive.uncompressed_size), archive.error or "OK")
    console.print(table)


# List filenames that are possibly different versions of the same item.
@app.command(help="Show possible filename-based version groups.")
def versions(
    database: Path = typer.Option(default_database_path(), "--database", "-d"),
    scan_id: int | None = typer.Option(None, "--scan-id"),
) -> None:
    selected_scan_id = scan_id if scan_id is not None else latest_scan_id(database)
    if selected_scan_id is None:
        raise typer.BadParameter("No completed scans found in this database.")
    groups = possible_version_groups(files_for_scan(database, selected_scan_id))
    if not groups:
        console.print(f"No possible version groups found in scan {selected_scan_id}.")
        return
    console.print(f"[bold]Possible version groups: scan {selected_scan_id}[/bold]")
    for group in groups:
        console.print(f"\n[bold]{group.base_name.title()}[/bold]")
        for file in group.files:
            console.print(file.path, soft_wrap=True)


# Export a saved scan as a JSON manifest or CSV file inventory.
@app.command(help="Export a saved scan to a .json or .csv file.")
def export(
    destination: Path = typer.Argument(..., help="Output filename ending in .json or .csv."),
    database: Path = typer.Option(default_database_path(), "--database", "-d"),
    scan_id: int | None = typer.Option(None, "--scan-id"),
) -> None:
    selected_scan_id = scan_id if scan_id is not None else latest_scan_id(database)
    if selected_scan_id is None:
        raise typer.BadParameter("No completed scans found in this database.")
    try:
        export_scan(database, selected_scan_id, destination)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    console.print(f"Exported scan {selected_scan_id} to {destination}.")


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


# Format an optional database timestamp for terminal output.
def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "In progress"
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


# Print the paths in one comparison category.
def _print_change_paths(label: str, files: list[object]) -> None:
    if not files:
        return
    console.print(f"\n[bold]{label}[/bold]")
    for file in files:
        console.print(file.path, soft_wrap=True)


if __name__ == "__main__":
    app()
