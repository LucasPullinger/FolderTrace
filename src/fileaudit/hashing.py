from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from fileaudit.scanner import FileRecord

CHUNK_SIZE = 1024 * 1024


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