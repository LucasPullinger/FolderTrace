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


@dataclass(frozen=True, slots=True)
class ScanResult:
    records: list[FileRecord]
    excluded: int


# Recursively return metadata for regular files within 'folder'.
def scan_folder(folder: Path) -> list[FileRecord]:
    return scan_folder_with_stats(folder).records


# Scan a folder while skipping paths matched by supplied glob patterns.
def scan_folder_with_stats(folder: Path, exclude_patterns: tuple[str, ...] = ()) -> ScanResult:
    root = folder.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    records: list[FileRecord] = []
    excluded = 0
    for path in root.rglob("*"):
        try:
            if not path.is_file():
                continue
            stat = path.stat()
        except OSError:
            continue
        relative_path = path.relative_to(root)
        if any(relative_path.match(pattern) or path.match(pattern) for pattern in exclude_patterns):
            excluded += 1
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

    return ScanResult(records, excluded)
