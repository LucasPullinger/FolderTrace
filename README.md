# FileAudit

FileAudit is a local-first application for scanning folders and building a structured, persistent inventory of their contents.

It helps answer practical questions about large file collections:

- What files are in this folder?
- Which files are exact duplicates?
- What is stored inside my archives?
- What has changed since a previous scan?
- Can I recreate or verify this collection later?

FileAudit is designed for general-purpose collections such as downloads, project archives, photo backups, and datasets. Mod folders are a useful example, but not the product's primary focus.

## How it works

FileAudit recursively scans a selected directory, collects metadata for every file, calculates SHA-256 hashes, optionally inspects supported archives, and stores the resulting manifest locally. It then analyses that manifest to surface duplicates and changes over time.

```text
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
  "type": "zip",
  "modified": "2026-09-03T10:24:00",
  "archive_files": 142
}
```

## Planned MVP

The first version focuses on a small, reliable auditing workflow:

1. Recursively scan a folder and record each file's path, name, extension, size, and modification date.
2. Calculate SHA-256 hashes.
3. Detect and report exact duplicate files.
4. Recognise and inspect `.zip`, `.tar`, and `.tar.gz` archives without extracting them.
5. Persist scan manifests locally in SQLite.
6. Compare a new scan with an earlier one to report added, removed, changed, and unchanged files.

Archive records can include the number of contained files, total uncompressed size, and contained extensions.

## Exact duplicates vs. possible versions

FileAudit keeps these concepts deliberately separate.

| Finding                | Meaning                                                                             | Confidence   |
| ---------------------- | ----------------------------------------------------------------------------------- | ------------ |
| Exact duplicate        | Files have the same SHA-256 hash.                                                   | Definitive   |
| Possible version group | Filenames suggest related releases, such as`tool-v1.0.zip` and `tool-v2.0.zip`. | Interpretive |

Version grouping is a future feature and must never be presented as equivalent to hash-based duplicate detection.

## Command-line interface

The application will begin as a CLI. Intended commands include:

```bash
fileaudit scan ~/Downloads
fileaudit summary
fileaudit duplicates
fileaudit archives
fileaudit changes
fileaudit export manifest.json
```

An example scan summary:

```text
Scanning ~/Downloads...

Files:              284
Archives:            61
Total size:        14.8 GB

Exact duplicates:    12
Duplicate space:    2.3 GB

Possible version groups: 7
Archives with errors: 2
```

## Proposed architecture

```text
Python
│
├── Scanner             Finds files
├── Hasher              Calculates SHA-256
├── Archive Inspector   Reads archive contents
├── Database            Stores manifests
├── Analysis            Finds duplicates and changes
└── CLI                 Provides user commands
```

## Technology

- **Python 3.11+** — application language and standard-library support for filesystem scanning.
- **Typer** — command-line interface and argument validation.
- **Rich** — readable terminal tables and scan summaries.
- **SQLite** — local, serverless storage for persistent scan manifests.
- **SQLAlchemy** — Python database models and schema creation for the `scans` and `files` tables.
- **pytest** — automated scanner, CLI, hashing, and database tests.

`hashlib` provides SHA-256 hashing. Planned standard-library integrations include `zipfile` and `tarfile` for archive inspection. FileAudit runs entirely locally and does not require cloud services.

## Roadmap

1. Scan files and print metadata.
2. Calculate SHA-256 hashes.
3. Detect duplicate files.
4. Store scans in SQLite.
5. Compare scans.
6. Inspect archive contents.
7. Detect possible version groups.
8. Export manifests as JSON or CSV.
9. Optionally add a GUI.
10. Optionally add specialised plugins, such as a Nexus Mods integration.

## Non-goals

FileAudit is not a file manager, backup program, antivirus product, cloud storage system, archive replacement, or mod manager. It analyses and records a collection so that it can be understood, verified, and compared over time.

> Point FileAudit at a directory. It creates a persistent inventory of the files, detects exact duplicates, and tells you what changed between scans.
