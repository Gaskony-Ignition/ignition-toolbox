"""Tests for the project loader and inventory computation.

``mini_project`` fixture (see fixtures/mini_project/) is a hand-built,
two-view project with known counts:

- views: "Home" (root + 2 children) and "Popup/Confirm" (root + 1 child)
- component_count: 5 (2 flex roots, 1 label, 1 embedded view, 1 button)
- 1 real binding (Popup/Confirm's root has a tag binding on props.text)
- Popup/Confirm is only reachable because Home embeds it via ia.display.view
"""

import zipfile
from pathlib import Path

from ignition_toolkit.audit.project import PerspectiveProject

from .conftest import FIXTURES_DIR, load_project


def test_load_from_directory_finds_both_views() -> None:
    project = load_project("mini_project")

    assert project.name == "mini_project"
    assert set(project.views) == {"Home", "Popup/Confirm"}


def test_load_from_zip_matches_directory_load(tmp_path: Path) -> None:
    zip_path = tmp_path / "mini_project.zip"
    project_dir = FIXTURES_DIR / "mini_project"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(project_dir).as_posix())

    project = PerspectiveProject.load(zip_path)

    assert set(project.views) == {"Home", "Popup/Confirm"}
    assert project.inventory().component_count == 5


def test_inventory_counts() -> None:
    project = load_project("mini_project")

    inventory = project.inventory()

    assert inventory.view_count == 2
    assert inventory.component_count == 5
    assert inventory.component_count_by_type == {
        "ia.container.flex": 2,
        "ia.display.label": 1,
        "ia.display.view": 1,
        "ia.input.button": 1,
    }
    assert inventory.binding_count == 1
    assert inventory.views == ["Home", "Popup/Confirm"]


def test_embedded_view_is_reachable() -> None:
    project = load_project("mini_project")

    # Popup/Confirm isn't in page-config at all — it's only reachable because
    # Home embeds it via an ia.display.view component.
    assert project.unreachable_views() == []


def test_walk_yields_root_first_then_children_depth_first() -> None:
    project = load_project("mini_project")
    home = project.views["Home"]

    refs = list(home.walk())

    assert refs[0].component_path == "root"
    assert refs[0].depth == 0
    names = [ref.node.name for ref in refs]
    assert names == ["root", "Title", "ConfirmPopup"]


def test_load_missing_source_raises() -> None:
    try:
        PerspectiveProject.load("/no/such/path/at/all")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass
