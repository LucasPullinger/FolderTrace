from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine, inspect, select
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from foldertrace.scanner import FileRecord
from foldertrace.archives import inspect_archive


class Base(DeclarativeBase):
    pass


# A completed or in-progress scan of a single root folder.
class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    root_path: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# Metadata for one file discovered during a scan.
class StoredFile(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id"), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    extension: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))


class StoredArchive(Base):
    __tablename__ = "archives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False, unique=True)
    archive_type: Mapped[str] = mapped_column(String, nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    uncompressed_size: Mapped[int] = mapped_column(Integer, nullable=False)
    extensions: Mapped[str] = mapped_column(String, nullable=False)
    error: Mapped[str | None] = mapped_column(String)


# An exact-duplicate group from one saved scan.
class DuplicateGroup:
    def __init__(self, sha256: str, files: list[StoredFile]) -> None:
        self.sha256 = sha256
        self.files = files

    @property
    def duplicate_size(self) -> int:
        return sum(file.size for file in self.files[1:])


# Categorised differences between two saved scans.
@dataclass(frozen=True, slots=True)
class ScanChanges:
    added: list[StoredFile]
    removed: list[StoredFile]
    changed: list[StoredFile]
    unchanged: list[StoredFile]


# Return the default on-device location for FolderTrace's database.
def default_database_path() -> Path:
    return Path.home() / ".local" / "share" / "foldertrace" / "foldertrace.db"


# Create the SQLite engine and ensure FolderTrace's tables exist.
def create_database(database_path: Path) -> Engine:
    path = database_path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(path)))
    Base.metadata.create_all(engine)
    _migrate_files_table(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_files_sha256 ON files (sha256)"
        )
    return engine


# Add schema fields introduced after an existing SQLite database was created.
def _migrate_files_table(engine: Engine) -> None:
    column_names = {column["name"] for column in inspect(engine).get_columns("files")}
    if "sha256" not in column_names:
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE files ADD COLUMN sha256 VARCHAR(64)")


# Save a folder scan and return its persistent scan ID.
def save_scan(
    database_path: Path, root_path: Path, records: list[FileRecord]
) -> int:
    engine = create_database(database_path)
    with Session(engine, expire_on_commit=False) as session:
        scan = Scan(
            root_path=str(root_path.expanduser().resolve()),
            started_at=datetime.now(UTC),
        )
        session.add(scan)
        session.flush()

        session.add_all(
            StoredFile(
                scan_id=scan.id,
                path=str(record.path),
                name=record.name,
                extension=record.extension,
                size=record.size,
                modified_at=record.modified_at,
                sha256=record.sha256,
            )
            for record in records
        )
        session.flush()
        stored_files = list(session.scalars(select(StoredFile).where(StoredFile.scan_id == scan.id)))
        session.add_all(
            StoredArchive(
                file_id=file.id,
                archive_type=archive.archive_type,
                file_count=archive.file_count,
                uncompressed_size=archive.uncompressed_size,
                extensions=json.dumps(archive.extensions),
                error=archive.error,
            )
            for file in stored_files
            if (archive := inspect_archive(Path(file.path))) is not None
        )
        scan.completed_at = datetime.now(UTC)
        session.commit()
        return scan.id


# Return file rows for a saved scan. This supports reporting and tests.
def files_for_scan(database_path: Path, scan_id: int) -> list[StoredFile]:
    engine = create_database(database_path)
    with Session(engine) as session:
        return list(
            session.query(StoredFile)
            .filter(StoredFile.scan_id == scan_id)
            .order_by(StoredFile.path)
        )


# Return the most recently completed scan ID, if the database has any scans.
def latest_scan_id(database_path: Path) -> int | None:
    engine = create_database(database_path)
    with Session(engine) as session:
        return session.scalar(
            select(Scan.id).where(Scan.completed_at.is_not(None)).order_by(Scan.id.desc())
        )


# Return latest saved file records for a particular root folder.
def latest_files_for_root(database_path: Path, root_path: Path) -> dict[str, StoredFile]:
    engine = create_database(database_path)
    with Session(engine) as session:
        scan_id = session.scalar(select(Scan.id).where(Scan.root_path == str(root_path.expanduser().resolve())).order_by(Scan.id.desc()))
        if scan_id is None:
            return {}
        return {file.path: file for file in session.scalars(select(StoredFile).where(StoredFile.scan_id == scan_id))}


# Return saved scans from newest to oldest.
def saved_scans(database_path: Path) -> list[Scan]:
    engine = create_database(database_path)
    with Session(engine) as session:
        return list(session.scalars(select(Scan).order_by(Scan.id.desc())))


# Compare file paths and content between two saved scans.
def compare_scans(database_path: Path, from_scan_id: int, to_scan_id: int) -> ScanChanges:
    engine = create_database(database_path)
    with Session(engine) as session:
        from_scan = session.get(Scan, from_scan_id)
        to_scan = session.get(Scan, to_scan_id)
        if from_scan is None:
            raise ValueError(f"Scan {from_scan_id} does not exist.")
        if to_scan is None:
            raise ValueError(f"Scan {to_scan_id} does not exist.")

        from_files = list(
            session.scalars(select(StoredFile).where(StoredFile.scan_id == from_scan_id))
        )
        to_files = list(
            session.scalars(select(StoredFile).where(StoredFile.scan_id == to_scan_id))
        )

    from_by_path = {file.path: file for file in from_files}
    to_by_path = {file.path: file for file in to_files}
    added = [file for path, file in to_by_path.items() if path not in from_by_path]
    removed = [file for path, file in from_by_path.items() if path not in to_by_path]
    changed: list[StoredFile] = []
    unchanged: list[StoredFile] = []

    for path in from_by_path.keys() & to_by_path.keys():
        if _files_match(from_by_path[path], to_by_path[path]):
            unchanged.append(to_by_path[path])
        else:
            changed.append(to_by_path[path])

    return ScanChanges(
        added=sorted(added, key=lambda file: file.path),
        removed=sorted(removed, key=lambda file: file.path),
        changed=sorted(changed, key=lambda file: file.path),
        unchanged=sorted(unchanged, key=lambda file: file.path),
    )


# Compare SHA-256 hashes when available, with metadata support for legacy scans.
def _files_match(first: StoredFile, second: StoredFile) -> bool:
    if first.sha256 is not None and second.sha256 is not None:
        return first.sha256 == second.sha256
    return first.size == second.size and first.modified_at == second.modified_at


# Return exact duplicate groups for one scan, based on matching SHA-256 hashes.
def duplicate_groups(database_path: Path, scan_id: int) -> list[DuplicateGroup]:
    engine = create_database(database_path)
    with Session(engine) as session:
        rows = session.scalars(
            select(StoredFile)
            .where(StoredFile.scan_id == scan_id, StoredFile.sha256.is_not(None))
            .order_by(StoredFile.sha256, StoredFile.path)
        ).all()

    files_by_hash: dict[str, list[StoredFile]] = {}
    for file in rows:
        if file.sha256 is not None:
            files_by_hash.setdefault(file.sha256, []).append(file)

    return [
        DuplicateGroup(sha256, files)
        for sha256, files in files_by_hash.items()
        if len(files) > 1
    ]


# Return stored archive metadata for one scan.
def archives_for_scan(database_path: Path, scan_id: int) -> list[tuple[StoredFile, StoredArchive]]:
    engine = create_database(database_path)
    with Session(engine) as session:
        return list(
            session.execute(
                select(StoredFile, StoredArchive)
                .join(StoredArchive, StoredArchive.file_id == StoredFile.id)
                .where(StoredFile.scan_id == scan_id)
                .order_by(StoredFile.path)
            )
        )
