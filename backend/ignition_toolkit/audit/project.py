"""
Perspective project loader — turns a project export (directory or zip) into
a queryable in-memory model for the audit rule engine.

Ignition Perspective resources are plain JSON on disk. A full gateway/Designer
export looks like::

    <ProjectName>/
      com.inductiveautomation.perspective/
        views/<ViewPath>/view.json
        page-config/config.json
        style-classes/<name>/style.json
        stylesheet/stylesheet.css

Real gateway mirrors seen in the field are sometimes flatter (no
``com.inductiveautomation.perspective`` wrapper, a ``_meta/page-config.json``
summary instead of the standard resource) — see
``/home/nigel/claude/ignition/home/project_mirror`` for an example. The
loader in this module tolerates both shapes: it searches for a
``com.inductiveautomation.perspective/views`` prefix first and falls back to
treating the whole source tree as the views root.

Only the fields the audit rules need are modelled; everything else on a
component node is preserved via ``extra="allow"`` so we never silently drop
information a future rule might need.
"""

import json
import logging
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

_PERSPECTIVE_MARKER = "com.inductiveautomation.perspective/views/"
_STANDARD_PAGE_CONFIG = "com.inductiveautomation.perspective/page-config/config.json"
_MIRROR_PAGE_CONFIG_NAME = "_meta/page-config.json"


class _SourceTree:
    """Uniform read-only view over a project directory or a zip export.

    Listing is metadata-only (cheap even for large exports); file contents
    are only read on demand via :meth:`read_text` so a multi-hundred-MB
    project export doesn't need to be loaded into memory up front.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._is_zip = root.is_file()
        self._zip: zipfile.ZipFile | None = zipfile.ZipFile(root) if self._is_zip else None

    def list_files(self) -> list[str]:
        """Return every regular file's path, POSIX-separated, relative to the root."""
        if self._zip is not None:
            return [name for name in self._zip.namelist() if not name.endswith("/")]
        return [p.relative_to(self._root).as_posix() for p in self._root.rglob("*") if p.is_file()]

    def read_text(self, relative_path: str) -> str:
        if self._zip is not None:
            return self._zip.read(relative_path).decode("utf-8")
        return (self._root / relative_path).read_text(encoding="utf-8")

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()


class ComponentNode(BaseModel):
    """One node in a view's component tree (``root`` or any descendant).

    ``extra="allow"`` means every key Ignition happens to emit round-trips
    even though only the ones audit rules use are declared explicitly.
    """

    # Ignition's wire format uses camelCase ("propConfig"); pep8-naming wants
    # snake_case attributes, so the field is aliased — see the equivalent note
    # in ignition_toolkit/udt/models.py for the same pattern.
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    props: dict[str, Any] = Field(default_factory=dict)
    position: dict[str, Any] = Field(default_factory=dict)
    events: dict[str, Any] = Field(default_factory=dict)
    scripts: dict[str, Any] = Field(default_factory=dict)
    prop_config: dict[str, Any] = Field(default_factory=dict, alias="propConfig")
    children: list["ComponentNode"] = Field(default_factory=list)

    @property
    def name(self) -> str:
        return self.meta.get("name") or "(unnamed)"


ComponentNode.model_rebuild()


@dataclass(frozen=True)
class ComponentRef:
    """A component node plus its location within a view.

    ``component_path`` is a ``/``-separated chain of component names from
    the view root (e.g. ``"root/FlexContainer/Label_1"``), used to build
    ``Finding.location`` strings.
    """

    view_path: str
    component_path: str
    depth: int
    node: ComponentNode

    @property
    def location(self) -> str:
        return f"{self.view_path} > {self.component_path}"


class PerspectiveView(BaseModel):
    """A single ``view.json``, plus the project-relative path it lives at."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    path: str
    custom: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    props: dict[str, Any] = Field(default_factory=dict)
    prop_config: dict[str, Any] = Field(default_factory=dict, alias="propConfig")
    root: ComponentNode

    def walk(self) -> Iterator[ComponentRef]:
        """Depth-first walk of every component in this view, root included."""

        def _walk(node: ComponentNode, path: str, depth: int) -> Iterator[ComponentRef]:
            yield ComponentRef(self.path, path, depth, node)
            for child in node.children:
                yield from _walk(child, f"{path}/{child.name}", depth + 1)

        yield from _walk(self.root, "root", 0)

    def embedded_view_paths(self) -> set[str]:
        """View paths this view embeds: ``ia.display.view`` and tab/carousel children."""
        found: set[str] = set()
        for ref in self.walk():
            node = ref.node
            if node.type == "ia.display.view":
                embedded_path = node.props.get("path")
                if isinstance(embedded_path, str) and embedded_path:
                    found.add(embedded_path)
            for tab in node.props.get("tabs") or []:
                view_path = tab.get("viewPath") if isinstance(tab, dict) else None
                if view_path:
                    found.add(view_path)
            for carousel_view in node.props.get("views") or []:
                view_path = (
                    carousel_view.get("viewPath") if isinstance(carousel_view, dict) else None
                )
                if view_path:
                    found.add(view_path)
        return found

    def iter_bindings(self) -> Iterator[tuple[ComponentRef, str, dict[str, Any]]]:
        """Yield (component, prop path, binding config) for every real binding.

        ``propConfig`` entries that only carry metadata (e.g. ``persistent``
        on a param, with no ``binding`` key) are skipped.
        """
        for ref in self.walk():
            for prop_path, config in ref.node.prop_config.items():
                if isinstance(config, dict) and "binding" in config:
                    yield ref, prop_path, config["binding"]


@dataclass
class Inventory:
    """Summary counts for a project, used in the report's executive summary."""

    view_count: int
    component_count: int
    component_count_by_type: dict[str, int]
    binding_count: int
    views: list[str] = field(default_factory=list)


class PerspectiveProject:
    """A loaded Perspective project: its views, indexed by project-relative path."""

    def __init__(
        self,
        name: str,
        views: dict[str, PerspectiveView],
        page_config: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.views = views
        self.page_config = page_config or {}

    @classmethod
    def load(cls, source: str | Path) -> "PerspectiveProject":
        """Load a project from a directory or a zip file (project export)."""
        root = Path(source)
        if not root.exists():
            raise FileNotFoundError(f"Perspective project source not found: {root}")

        tree = _SourceTree(root)
        try:
            all_files = tree.list_files()
            views_prefix = _find_views_prefix(all_files)
            views = _load_views(tree, all_files, views_prefix)
            page_config = _load_page_config(tree, all_files)
        finally:
            tree.close()

        return cls(
            name=root.stem if root.is_file() else root.name, views=views, page_config=page_config
        )

    def inventory(self) -> Inventory:
        """Compute view/component/binding counts across the whole project."""
        component_count = 0
        component_count_by_type: dict[str, int] = {}
        binding_count = 0

        for view in self.views.values():
            for ref in view.walk():
                component_count += 1
                type_name = ref.node.type or "(untyped)"
                component_count_by_type[type_name] = component_count_by_type.get(type_name, 0) + 1
            binding_count += sum(1 for _ in view.iter_bindings())

        return Inventory(
            view_count=len(self.views),
            component_count=component_count,
            component_count_by_type=component_count_by_type,
            binding_count=binding_count,
            views=sorted(self.views),
        )

    def reachable_view_paths(self) -> set[str]:
        """Every view path reachable from page-config routes/docks or an embedding."""
        reachable: set[str] = set()

        pages = self.page_config.get("pages", {})
        if isinstance(pages, dict):
            for page in pages.values():
                view_path = page.get("viewPath") if isinstance(page, dict) else None
                if view_path:
                    reachable.add(view_path)

        shared_docks = self.page_config.get("sharedDocks", {})
        if isinstance(shared_docks, dict):
            for docks in shared_docks.values():
                if not isinstance(docks, list):
                    continue
                for dock in docks:
                    view_path = dock.get("viewPath") if isinstance(dock, dict) else None
                    if view_path:
                        reachable.add(view_path)

        for view in self.views.values():
            reachable |= view.embedded_view_paths()

        return reachable

    def unreachable_views(self) -> list[str]:
        """View paths present in the project but not reachable from any route/dock/embed."""
        return sorted(set(self.views) - self.reachable_view_paths())


def _find_views_prefix(all_files: list[str]) -> str:
    """Locate the ``.../com.inductiveautomation.perspective/views/`` prefix, if present.

    Falls back to "" (treat the whole source tree as the views root) for
    flatter mirrors that don't carry the standard resource wrapper.
    """
    for path in all_files:
        idx = path.find(_PERSPECTIVE_MARKER)
        if idx != -1:
            return path[: idx + len(_PERSPECTIVE_MARKER)]
    return ""


def _load_views(
    tree: _SourceTree, all_files: list[str], views_prefix: str
) -> dict[str, PerspectiveView]:
    views: dict[str, PerspectiveView] = {}
    suffix = "/view.json"
    for path in all_files:
        if not path.endswith(suffix):
            continue
        if views_prefix and not path.startswith(views_prefix):
            continue
        relative = path[len(views_prefix) :] if views_prefix else path
        view_path = relative[: -len(suffix)]
        if not view_path:
            continue
        try:
            raw = json.loads(tree.read_text(path))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Skipping unparseable view.json at %s: %s", path, exc)
            continue
        raw.setdefault("root", {})
        views[view_path] = PerspectiveView(path=view_path, **raw)
    return views


def _load_page_config(tree: _SourceTree, all_files: list[str]) -> dict[str, Any]:
    candidates = [p for p in all_files if p.endswith(_STANDARD_PAGE_CONFIG)]
    candidates += [p for p in all_files if p.endswith(_MIRROR_PAGE_CONFIG_NAME)]
    for path in candidates:
        try:
            return dict(json.loads(tree.read_text(path)))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Skipping unparseable page-config at %s: %s", path, exc)
    return {}
