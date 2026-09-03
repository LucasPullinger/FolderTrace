from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path

from foldertrace.database import archives_for_scan, files_for_scan, saved_scans


# Export one saved scan to JSON or CSV, based on the destination suffix.
def export_scan(database_path: Path, scan_id: int, destination: Path) -> None:
    scan = next((scan for scan in saved_scans(database_path) if scan.id == scan_id), None)
    if scan is None:
        raise ValueError(f"Scan {scan_id} does not exist.")
    files = files_for_scan(database_path, scan_id)
    archive_by_file_id = {archive.file_id: archive for file, archive in archives_for_scan(database_path, scan_id)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() == ".json":
        _write_json(destination, scan, files, archive_by_file_id)
    elif destination.suffix.lower() == ".csv":
        _write_csv(destination, files, archive_by_file_id)
    else:
        raise ValueError("Output filename must end in .json or .csv.")


# Write a complete nested scan manifest.
def _write_json(destination: Path, scan: object, files: list[object], archives: dict[int, object]) -> None:
    payload = {
        "scan": {"id": scan.id, "root_path": scan.root_path, "started_at": _timestamp(scan.started_at), "completed_at": _timestamp(scan.completed_at)},
        "files": [
            {
                "path": file.path, "name": file.name, "extension": file.extension,
                "size": file.size, "modified_at": _timestamp(file.modified_at), "sha256": file.sha256,
                "archive": _archive_data(archives.get(file.id)),
            }
            for file in files
        ],
    }
    destination.write_text(json.dumps(payload, indent=2) + "\n")


# Write a flat file inventory suitable for spreadsheets and databases.
def _write_csv(destination: Path, files: list[object], archives: dict[int, object]) -> None:
    fields = ["path", "name", "extension", "size", "modified_at", "sha256", "archive_type", "archive_file_count", "archive_uncompressed_size", "archive_error"]
    with destination.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for file in files:
            archive = archives.get(file.id)
            writer.writerow({"path": file.path, "name": file.name, "extension": file.extension, "size": file.size, "modified_at": _timestamp(file.modified_at), "sha256": file.sha256, "archive_type": getattr(archive, "archive_type", None), "archive_file_count": getattr(archive, "file_count", None), "archive_uncompressed_size": getattr(archive, "uncompressed_size", None), "archive_error": getattr(archive, "error", None)})


def _archive_data(archive: object | None) -> dict[str, object] | None:
    if archive is None:
        return None
    return {"type": archive.archive_type, "file_count": archive.file_count, "uncompressed_size": archive.uncompressed_size, "extensions": json.loads(archive.extensions), "error": archive.error}


def _timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
