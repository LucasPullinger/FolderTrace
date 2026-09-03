from pathlib import Path

from typer.testing import CliRunner

from foldertrace.cli import app
from foldertrace.database import save_scan
from foldertrace.hashing import hash_records
from foldertrace.scanner import scan_folder


runner = CliRunner()


def test_scan_command_prints_a_summary(tmp_path: Path) -> None:
    (tmp_path / "report.txt").write_text("audit")
    database = tmp_path / "foldertrace.db"

    result = runner.invoke(app, ["scan", str(tmp_path), "--database", str(database)])

    assert result.exit_code == 0
    assert "Scan complete" in result.stdout
    assert "Files" in result.stdout
    assert "1" in result.stdout
    assert "5 B" in result.stdout
    assert database.exists()


def test_duplicates_command_prints_matching_files(tmp_path: Path) -> None:
    (tmp_path / "first.txt").write_text("same")
    (tmp_path / "second.txt").write_text("same")
    database = tmp_path / "foldertrace.db"
    runner.invoke(app, ["scan", str(tmp_path), "--database", str(database)])

    result = runner.invoke(app, ["duplicates", "--database", str(database)])

    assert result.exit_code == 0
    assert "Exact duplicates" in result.stdout
    assert "first.txt" in result.stdout
    assert "second.txt" in result.stdout


def test_scans_command_lists_saved_scans(tmp_path: Path) -> None:
    (tmp_path / "report.txt").write_text("audit")
    database = tmp_path / "foldertrace.db"
    runner.invoke(app, ["scan", str(tmp_path), "--database", str(database)])

    result = runner.invoke(app, ["scans", "--database", str(database)])

    assert result.exit_code == 0
    assert "Saved scans" in result.stdout
    assert "Folder" in result.stdout


def test_summary_command_prints_scan_overview(tmp_path: Path) -> None:
    (tmp_path / "report.txt").write_text("audit")
    database = tmp_path / "foldertrace.db"
    runner.invoke(app, ["scan", str(tmp_path), "--database", str(database)])

    result = runner.invoke(app, ["summary", "--database", str(database)])

    assert result.exit_code == 0
    assert "Scan summary" in result.stdout
    assert "Duplicate groups" in result.stdout


def test_changes_command_prints_summary_and_details(tmp_path: Path) -> None:
    source_folder = tmp_path / "source"
    source_folder.mkdir()
    (source_folder / "removed.txt").write_text("old")
    database = tmp_path / "foldertrace.db"
    first_scan_id = save_scan(database, source_folder, hash_records(scan_folder(source_folder)))
    (source_folder / "removed.txt").unlink()
    (source_folder / "added.txt").write_text("new")
    second_scan_id = save_scan(database, source_folder, hash_records(scan_folder(source_folder)))

    result = runner.invoke(
        app,
        [
            "changes",
            "--from",
            str(first_scan_id),
            "--to",
            str(second_scan_id),
            "--details",
            "--database",
            str(database),
        ],
    )

    assert result.exit_code == 0
    assert "Scan changes" in result.stdout
    assert "added.txt" in result.stdout
    assert "removed.txt" in result.stdout


def test_search_command_prints_matching_files(tmp_path: Path) -> None:
    (tmp_path / "annual-report.pdf").write_text("report")
    (tmp_path / "notes.txt").write_text("notes")
    database = tmp_path / "foldertrace.db"
    runner.invoke(app, ["scan", str(tmp_path), "--database", str(database)])

    result = runner.invoke(app, ["search", "report", "--database", str(database)])

    assert result.exit_code == 0
    assert "Search results" in result.stdout
    assert "annual-report.pdf" in result.stdout
    assert "notes.txt" not in result.stdout
