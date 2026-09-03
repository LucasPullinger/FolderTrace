from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path

from foldertrace.scanner import FileRecord

CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class HashingResult:
    records: list[FileRecord]
    reused: int
    calculated: int


# Calculate a file's SHA-256 digest without loading the entire file into memory.
def hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


# Add SHA-256 digests to file records, retaining records that cannot be read.
def hash_records(records: list[FileRecord]) -> list[FileRecord]:
    hashed_records: list[FileRecord] = []
    for record in records:
        try:
            hashed_records.append(replace(record, sha256=hash_file(record.path)))
        except OSError:
            hashed_records.append(record)
    return hashed_records


# Hash files while reusing hashes from unchanged records in the previous scan.
def hash_records_incrementally(records: list[FileRecord], previous: dict[str, object]) -> HashingResult:
    result: list[FileRecord] = []
    reused = 0
    calculated = 0
    for record in records:
        old = previous.get(str(record.path))
        if old and old.sha256 and old.size == record.size and old.modified_at == record.modified_at:
            result.append(replace(record, sha256=old.sha256))
            reused += 1
        else:
            try:
                result.append(replace(record, sha256=hash_file(record.path)))
                calculated += 1
            except OSError:
                result.append(record)
    return HashingResult(result, reused, calculated)
