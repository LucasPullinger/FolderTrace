import json
from pathlib import Path

from foldertrace.database import save_scan
from foldertrace.exporting import export_scan
from foldertrace.hashing import hash_records
from foldertrace.scanner import scan_folder


def test_export_scan_writes_json_and_csv(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "report.txt").write_text("audit")
    database = tmp_path / "foldertrace.db"
    scan_id = save_scan(database, source, hash_records(scan_folder(source)))
    json_file = tmp_path / "manifest.json"
    csv_file = tmp_path / "manifest.csv"

    export_scan(database, scan_id, json_file)
    export_scan(database, scan_id, csv_file)

    assert json.loads(json_file.read_text())["files"][0]["name"] == "report.txt"
    assert "report.txt" in csv_file.read_text()
