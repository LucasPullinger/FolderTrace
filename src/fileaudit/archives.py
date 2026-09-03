from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import tarfile
import zipfile


@dataclass(frozen=True, slots=True)
class ArchiveInfo:
    archive_type: str
    file_count: int
    uncompressed_size: int
    extensions: tuple[str, ...]
    error: str | None = None


# Inspect supported archives without extracting their contents.
def inspect_archive(path: Path) -> ArchiveInfo | None:
    name = path.name.lower()
    archive_type = "zip" if name.endswith(".zip") else "tar.gz" if name.endswith((".tar.gz", ".tgz")) else "tar" if name.endswith(".tar") else None
    if archive_type is None:
        return None
    try:
        if archive_type == "zip":
            with zipfile.ZipFile(path) as archive:
                members = [(member.filename, member.file_size) for member in archive.infolist() if not member.is_dir()]
        else:
            with tarfile.open(path, "r:*") as archive:
                members = [(member.name, member.size) for member in archive.getmembers() if member.isfile()]
        extensions = tuple(sorted({PurePosixPath(member[0]).suffix.lower() for member in members if PurePosixPath(member[0]).suffix}))
        return ArchiveInfo(archive_type, len(members), sum(member[1] for member in members), extensions)
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        return ArchiveInfo(archive_type, 0, 0, (), str(error))
