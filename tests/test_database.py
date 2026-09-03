from pathlib import Path
import sqlite3

from fileaudit.database import (
    create_database,
    duplicate_groups,
    files_for_scan,
    save_scan,
    saved_scans,
)
from fileaudit.hashing import hash_records
from fileaudit.scanner import scan_folder


def test_save_scan_persists_file_records(tmp_path: Path) -> None:
    source_folder = tmp_path / "source"
    source_folder.mkdir()
    (source_folder / "report.txt").write_text("audit")
    database = tmp_path / "data" / "fileaudit.db"

    scan_id = save_scan(database, source_folder, hash_records(scan_folder(source_folder)))

    saved_files = files_for_scan(database, scan_id)
    assert database.exists()
    assert scan_id == 1
    assert len(saved_files) == 1
    assert saved_files[0].path == str(source_folder / "report.txt")
    assert saved_files[0].name == "report.txt"
    assert saved_files[0].extension == ".txt"
    assert saved_files[0].size == 5
    assert saved_files[0].sha256 is not None


def test_duplicate_groups_returns_matching_file_hashes(tmp_path: Path) -> None:
    source_folder = tmp_path / "source"
    source_folder.mkdir()
    (source_folder / "first.txt").write_text("same content")
    (source_folder / "second.txt").write_text("same content")
    (source_folder / "other.txt").write_text("different content")
    database = tmp_path / "fileaudit.db"

    scan_id = save_scan(database, source_folder, hash_records(scan_folder(source_folder)))

    groups = duplicate_groups(database, scan_id)
    assert len(groups) == 1
    assert len(groups[0].files) == 2
    assert {file.name for file in groups[0].files} == {"first.txt", "second.txt"}
    assert groups[0].duplicate_size == len("same content")


def test_create_database_adds_sha256_to_an_existing_files_table(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE scans (
                id INTEGER PRIMARY KEY,
                root_path VARCHAR NOT NULL,
                started_at DATETIME NOT NULL,
                completed_at DATETIME
            );
            CREATE TABLE files (
                id INTEGER PRIMARY KEY,
                scan_id INTEGER NOT NULL,
                path VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                extension VARCHAR NOT NULL,
                size INTEGER NOT NULL,
                modified_at DATETIME NOT NULL
            );
            """
        )

    create_database(database)

    with sqlite3.connect(database) as connection:
        column_names = {row[1] for row in connection.execute("PRAGMA table_info(files)")}
    assert "sha256" in column_names


def test_saved_scans_returns_newest_scan_first(tmp_path: Path) -> None:
    source_folder = tmp_path / "source"
    source_folder.mkdir()
    (source_folder / "report.txt").write_text("audit")
    database = tmp_path / "fileaudit.db"

    first_scan_id = save_scan(database, source_folder, hash_records(scan_folder(source_folder)))
    second_scan_id = save_scan(database, source_folder, hash_records(scan_folder(source_folder)))

    scans = saved_scans(database)
    assert [scan.id for scan in scans] == [second_scan_id, first_scan_id]
    assert scans[0].root_path == str(source_folder)
    assert scans[0].completed_at is not None
