from pathlib import Path

from typer.testing import CliRunner

from fileaudit.cli import app


runner = CliRunner()


def test_scan_command_prints_a_summary(tmp_path: Path) -> None:
    (tmp_path / "report.txt").write_text("audit")
    database = tmp_path / "fileaudit.db"

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
    database = tmp_path / "fileaudit.db"
    runner.invoke(app, ["scan", str(tmp_path), "--database", str(database)])

    result = runner.invoke(app, ["duplicates", "--database", str(database)])

    assert result.exit_code == 0
    assert "Exact duplicates" in result.stdout
    assert "first.txt" in result.stdout
    assert "second.txt" in result.stdout