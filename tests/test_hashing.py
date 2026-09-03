from pathlib import Path

from foldertrace.hashing import hash_file, hash_records, hash_records_incrementally
from foldertrace.scanner import scan_folder


def test_hash_file_returns_a_sha256_digest(tmp_path: Path) -> None:
    source_file = tmp_path / "message.txt"
    source_file.write_text("hello")

    digest = hash_file(source_file)

    assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_hash_records_adds_a_digest_to_each_file_record(tmp_path: Path) -> None:
    source_file = tmp_path / "message.txt"
    source_file.write_text("hello")

    records = hash_records(scan_folder(tmp_path))

    assert records[0].sha256 is not None


def test_incremental_hashing_reuses_an_unchanged_hash(tmp_path: Path) -> None:
    source_file = tmp_path / "message.txt"
    source_file.write_text("hello")
    previous_record = hash_records(scan_folder(tmp_path))[0]

    result = hash_records_incrementally(scan_folder(tmp_path), {str(source_file): previous_record})

    assert result.reused == 1
    assert result.calculated == 0
