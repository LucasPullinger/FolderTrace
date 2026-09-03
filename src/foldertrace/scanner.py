from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# Metadata captured for one regular file during a scan.
@dataclass(frozen=True, slots=True)
class FileRecord:
    path: Path
    name: str
    extension: str
    size: int
    modified_at: datetime
    sha256: str | None = None


# Recursively return metadata for regular files within 'folder'.
def scan_folder(folder: Path) -> list[FileRecord]:
    root = folder.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    records: list[FileRecord] = []
    for path in root.rglob("*"):
        try:
            if not path.is_file():
                continue
            stat = path.stat()
        except OSError:
            continue

        records.append(
            FileRecord(
                path=path,
                name=path.name,
                extension=path.suffix.lower(),
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime).astimezone(),
            )
        )

    return records