from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Protocol


class NamedFile(Protocol):
    name: str
    path: str


@dataclass(frozen=True, slots=True)
class VersionGroup:
    base_name: str
    files: list[NamedFile]


# Group files whose names differ only by common version, date, or copy markers.
def possible_version_groups(files: list[NamedFile]) -> list[VersionGroup]:
    groups: dict[str, list[NamedFile]] = {}
    for file in files:
        base_name = normalise_filename(file.name)
        if len(base_name) >= 3:
            groups.setdefault(base_name, []).append(file)
    return [
        VersionGroup(base_name, sorted(group, key=lambda file: file.path))
        for base_name, group in sorted(groups.items())
        if len(group) > 1
    ]


# Remove extensions and common release markers from a filename.
def normalise_filename(filename: str) -> str:
    name = filename.casefold()
    for suffix in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    else:
        name = Path(name).stem
    name = name.replace("_", " ")
    name = re.sub(r"\b(?:v|ver|version)?\s*\d+(?:[._-]\d+){1,3}\b", " ", name)
    name = re.sub(r"\b\d{4}[-_.]\d{1,2}[-_.]\d{1,2}\b", " ", name)
    name = re.sub(r"\b(?:final|latest|copy|backup|old|new)\b", " ", name)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", name)).strip()
