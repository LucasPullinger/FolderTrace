from pathlib import Path

import pytest

from fileaudit.scanner import scan_folder


def test_scan_folder_recursively_collects_file_metadata(tmp_path: Path) -> None:
    first_file = tmp_path / "notes.TXT"
    first_file.write_text("hello")
    nested_file = tmp_path / "nested" / "photo.jpg"
    nested_file.parent.mkdir()
    nested_file.write_bytes(b"abc")

    records = scan_folder(tmp_path)

    by_path = {record.path: record for record in records}
    assert set(by_path) == {first_file, nested_file}
    assert by_path[first_file].name == "notes.TXT"
    assert by_path[first_file].extension == ".txt"
    assert by_path[first_file].size == 5
    assert by_path[nested_file].extension == ".jpg"
    assert by_path[nested_file].size == 3
    assert by_path[first_file].modified_at.tzinfo is not None


def test_scan_folder_rejects_a_file(tmp_path: Path) -> None:
    source_file = tmp_path / "not-a-folder.txt"
    source_file.touch()

    with pytest.raises(NotADirectoryError):
        scan_folder(source_file)