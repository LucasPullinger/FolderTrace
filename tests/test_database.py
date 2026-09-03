from pathlib import Path

from fileaudit.database import files_for_scan, save_scan
from fileaudit.scanner import scan_folder


def test_save_scan_persists_file_records(tmp_path: Path) -> None:
    source_folder = tmp_path / "source"
    source_folder.mkdir()
    (source_folder / "report.txt").write_text("audit")
    database = tmp_path / "data" / "fileaudit.db"

    scan_id = save_scan(database, source_folder, scan_folder(source_folder))

    saved_files = files_for_scan(database, scan_id)
    assert database.exists()
    assert scan_id == 1
    assert len(saved_files) == 1
    assert saved_files[0].path == str(source_folder / "report.txt")
    assert saved_files[0].name == "report.txt"
    assert saved_files[0].extension == ".txt"
    assert saved_files[0].size == 5
