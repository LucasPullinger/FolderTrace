from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

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
) -> None:
    records = scan_folder(folder)
    total_size = sum(record.size for record in records)

    table = Table(title="Scan complete", show_header=False)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value")
    table.add_row("Scanned", str(folder))
    table.add_row("Files", str(len(records)))
    table.add_row("Total size", _format_size(total_size))
    console.print(table)


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