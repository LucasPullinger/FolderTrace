from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine, inspect, select
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from fileaudit.scanner import FileRecord


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


# An exact-duplicate group from one saved scan.
class DuplicateGroup:
    def __init__(self, sha256: str, files: list[StoredFile]) -> None:
        self.sha256 = sha256
        self.files = files

    @property
    def duplicate_size(self) -> int:
        return sum(file.size for file in self.files[1:])


# Return the default on-device location for FileAudit's database.
def default_database_path() -> Path:
    return Path.home() / ".local" / "share" / "fileaudit" / "fileaudit.db"


# Create the SQLite engine and ensure FileAudit's tables exist.
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