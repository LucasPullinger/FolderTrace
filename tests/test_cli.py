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
