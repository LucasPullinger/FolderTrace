from dataclasses import dataclass

from foldertrace.versions import normalise_filename, possible_version_groups


@dataclass
class ExampleFile:
    name: str
    path: str


def test_normalise_filename_removes_versions_and_markers() -> None:
    assert normalise_filename("SkyUI_v5.2-final.zip") == "skyui"
    assert normalise_filename("project-2026-09-03.tar.gz") == "project"


def test_possible_version_groups_only_returns_related_names() -> None:
    files = [
        ExampleFile("SkyUI_v5.1.zip", "/files/skyui-1"),
        ExampleFile("SkyUI_v5.2.zip", "/files/skyui-2"),
        ExampleFile("manifest.json", "/files/one/manifest.json"),
        ExampleFile("manifest.json", "/files/two/manifest.json"),
        ExampleFile("unrelated.zip", "/files/unrelated"),
    ]

    groups = possible_version_groups(files)

    assert len(groups) == 1
    assert groups[0].base_name == "skyui"
    assert [file.name for file in groups[0].files] == ["SkyUI_v5.1.zip", "SkyUI_v5.2.zip"]
