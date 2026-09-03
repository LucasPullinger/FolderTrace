# FolderTrace

[![PyPI version](https://img.shields.io/pypi/v/foldertrace.svg)](https://pypi.org/project/foldertrace/)

FolderTrace is a local-first application for scanning folders and building a structured, persistent inventory of their contents.

Point FolderTrace at a directory. It creates a persistent inventory of the files, detects exact duplicates, and tells you what changed between scans.

It helps answer practical questions about large file collections:

- What files are in this folder?
- Which files are exact duplicates?
- What is stored inside my archives?
- What has changed since a previous scan?
- Can I recreate or verify this collection later?

FolderTrace is designed for general-purpose collections such as downloads, project archives, photo backups, and datasets. Mod folders are a useful example, but not the product's primary focus.

## Install

FolderTrace requires Python 3.11 or later.

### From PyPI (recommended)

```bash
pipx install foldertrace
```

After installation:

```bash
foldertrace --help
foldertrace scan ~/Downloads
foldertrace summary
```

### Latest development version

Install directly from GitHub if you want unreleased changes:

```bash
pipx install git+https://github.com/LucasPullinger/FolderTrace.git
```

### Run from source

To run FolderTrace from a local clone:

```bash
git clone https://github.com/LucasPullinger/FolderTrace.git
cd FolderTrace
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
pytest
```

## How it works

FolderTrace recursively scans a selected directory, collects metadata for every file, calculates SHA-256 hashes, optionally inspects supported archives, and stores the resulting manifest locally. It then analyses that manifest to surface duplicates and changes over time.

```
Select folder
    ↓
Scan files and collect metadata
    ↓
Calculate SHA-256 hashes
    ↓
Inspect supported archives
    ↓
Store manifest locally
    ↓
Analyse duplicates and changes
```

A file record may contain information like this:

```json
{
  "path": "/Users/lucas/Downloads/project-final.zip",
  "name": "project-final.zip",
  "size": 34829102,
  "sha256": "a893...",
  "modified_at": "2026-09-03T10:24:00+01:00",
  "archive": {
    "type": "zip",
    "file_count": 142
  }
}
```

## Features

The first release provides a small, reliable auditing workflow:

- Recursively scan a folder and record each file's path, name, extension, size, and modification date.
- Calculate SHA-256 hashes.
- Detect and report exact duplicate files.
- Recognise and inspect `.zip`, `.tar`, and `.tar.gz` archives without extracting them.
- Persist scan manifests locally in SQLite.
- Compare a new scan with an earlier one to report added, removed, changed, and unchanged files.
- Identify possible filename-based version groups.
- Export saved scans as JSON or CSV.
- Reuse hashes from unchanged files to speed up repeated scans.
- Exclude unwanted files with glob patterns or a `.foldertraceignore` file.

Archive records can include the number of contained files, total uncompressed size, and contained extensions.

## Exact duplicates vs. possible versions

FolderTrace keeps these concepts deliberately separate.

| Finding | Meaning | Confidence |
|---|---|---|
| Exact duplicate | Files have the same SHA-256 hash. | Definitive |
| Possible version group | Filenames suggest related releases, such as `tool-v1.0.zip` and `tool-v2.0.zip`. | Interpretive |

Version grouping is intentionally conservative: a group is only shown when at least one filename contains a version number or date marker. It must never be presented as equivalent to hash-based duplicate detection.

## Command-line interface

The application is a CLI:

```bash
foldertrace scan ~/Downloads
foldertrace summary
foldertrace scans
foldertrace duplicates
foldertrace archives
foldertrace versions
foldertrace changes --from 1 --to 2
foldertrace export manifest.json
foldertrace cleanup --keep-latest 3 --yes
```

Each scan is stored in SQLite at `~/.local/share/foldertrace/foldertrace.db` by default. Use `foldertrace --help` for the complete command reference.

Exclude paths from a scan with repeated glob patterns:

```bash
foldertrace scan ~/Downloads --exclude "*.tmp" --exclude ".DS_Store"
```

You can also create a `.foldertraceignore` file in the scanned folder:

```
*.tmp
.DS_Store
.venv/*
node_modules/*
```

Repeated scans reuse SHA-256 hashes for files whose path, size, and modification time are unchanged. FolderTrace displays progress and reports reused versus newly calculated hashes.

### Remove saved scans

`cleanup` removes scan records from FolderTrace's local database only; it never deletes files from the scanned folder. The `--yes` confirmation flag is required.

```bash
# Delete one saved scan.
foldertrace cleanup --scan-id 1 --yes

# Keep the latest three scans and delete older saved scans.
foldertrace cleanup --keep-latest 3 --yes

# Delete every saved scan from FolderTrace's database.
foldertrace cleanall --yes
```

An example comparison:

```
Scan changes: 1 → 2

Added:       12
Removed:      4
Changed:      7
Unchanged:  261
```

## Technology

- Python 3.11+ — application language and standard-library support for filesystem scanning.
- Typer — command-line interface and argument validation.
- Rich — readable terminal tables and scan summaries.
- SQLite — local, serverless storage for persistent scan manifests.
- SQLAlchemy — Python database models and schema creation for the scans and files tables.
- pytest — automated scanner, CLI, hashing, and database tests.

`hashlib` provides SHA-256 hashing, while `zipfile` and `tarfile` inspect supported archives. FolderTrace runs entirely locally and does not require cloud services.

## Roadmap

- Add optional GUI support.
- Add specialised plugins, such as a Nexus Mods integration.
- Expand archive-format support, including `.7z` and `.rar`.
- Improve scan filtering and reporting.

## Non-goals

FolderTrace is not a file manager, backup program, antivirus product, cloud storage system, archive replacement, or mod manager. It analyses and records a collection so that it can be understood, verified, and compared over time.

## License

FolderTrace is licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later). See [LICENSE](LICENSE).
