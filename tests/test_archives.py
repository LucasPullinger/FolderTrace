from pathlib import Path
import zipfile

from foldertrace.archives import inspect_archive


def test_inspect_archive_reads_zip_metadata(tmp_path: Path) -> None:
    archive_path = tmp_path / "files.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("notes/readme.txt", "hello")
        archive.writestr("images/photo.png", b"abc")

    info = inspect_archive(archive_path)

    assert info is not None
    assert info.archive_type == "zip"
    assert info.file_count == 2
    assert info.uncompressed_size == 8
    assert info.extensions == (".png", ".txt")
