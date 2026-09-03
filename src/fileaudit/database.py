from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine
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


# Return the default on-device location for FileAudit's database.
def default_database_path() -> Path:
    return Path.home() / ".local" / "share" / "fileaudit" / "fileaudit.db"


# Create the SQLite engine and ensure FileAudit's tables exist.
def create_database(database_path: Path) -> Engine:
    path = database_path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(path)))
    Base.metadata.create_all(engine)
    return engine


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