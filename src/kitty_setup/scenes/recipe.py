"""Declarative scene recipes — Phase 2 §12 (declarative half), roadmap bullet 7.

Front-end onto the unchanged ``launcher.launch_scene()`` engine: read a named
TOML recipe from the user's scenes directory and build the exact
``(layout, tab_title, tab_accent, list[Pane])`` arguments the imperative
``my-kitty scene launch --pane`` form produces. No kitten-call behavior lives
here — the wire algorithm is settled by the h25 probe and owned by
``launcher.py``.

The ``Pane`` dataclass is IMPORTED from :mod:`.launcher`; this module never
redefines it or coins parallel field names. The recognised ``[[pane]]`` keys are
derived from ``Pane``'s fields so the two forms can never silently diverge
(``feedback_compose_reuse_primitive_argv`` lesson).

Scene files are USER DATA at ``$XDG_CONFIG_HOME/kitty-setup/scenes/<name>.toml``
(fallback ``~/.config/kitty-setup/scenes/``) — deliberately separate from the
managed payload at ``~/.config/kitty/kitty-setup/``, so the installer never
writes them and uninstall never deletes them.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from kitty_setup.scenes.launcher import Pane

# Recognised top-level keys. ``pane`` is the array-of-tables holding the panes;
# the styling trio maps 1:1 onto ``launch_scene`` arguments.
_RECOGNISED_TOP: tuple[str, ...] = ("layout", "tab_title", "tab_accent", "pane")
_STYLE_KEYS: tuple[str, ...] = ("layout", "tab_title", "tab_accent")
# Recognised pane keys ARE the Pane field names — derived, never hand-copied.
_RECOGNISED_PANE: tuple[str, ...] = tuple(f.name for f in dataclasses.fields(Pane))


class SceneRecipeError(Exception):
    """Any loader-side failure: bad name, missing file, parse error, schema."""


def scenes_dir() -> Path:
    """Resolve the user's scenes directory.

    Honors ``$XDG_CONFIG_HOME`` (fallback ``~/.config``) → ``kitty-setup/scenes``.
    This is user data, distinct from the managed payload under
    ``~/.config/kitty/kitty-setup/``; nothing in the installer writes here.
    """
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "kitty-setup" / "scenes"


def _guard_name(name: str) -> None:
    """Reject a scene name that could escape the scenes directory.

    A name becomes a filename, so a path separator or ``..`` segment is a
    traversal vector. Raise :class:`SceneRecipeError` before any IO.
    """
    if not name:
        raise SceneRecipeError("scene name is empty")
    seps = {"/", os.sep}
    if os.altsep:
        seps.add(os.altsep)
    if any(s in name for s in seps):
        raise SceneRecipeError(f"invalid scene name {name!r}: must not contain a path separator")
    if name == ".." or ".." in name.split("/"):
        raise SceneRecipeError(f"invalid scene name {name!r}: '..' is not allowed")


def _normalise(value: str | None) -> str | None:
    """Empty string → ``None`` (absent), mirroring ``parse_pane_spec``."""
    return value if value else None


def _require_str(value: object, *, key: str) -> str:
    """Return ``value`` as a str. A NUL is refused: ``subprocess.run`` cannot pass one in argv."""
    if not isinstance(value, str):
        raise SceneRecipeError(f"key '{key}' must be a string, got {type(value).__name__}")
    if "\x00" in value:
        raise SceneRecipeError(
            f"key '{key}' holds a NUL character, which no argv element can carry"
        )
    return value


def _build_pane(raw: object, *, index: int) -> Pane:
    if not isinstance(raw, dict):
        raise SceneRecipeError(
            f"[[pane]] entry #{index + 1} must be a table, got {type(raw).__name__}"
        )
    table = cast("dict[str, object]", raw)
    for key in table:
        if key not in _RECOGNISED_PANE:
            raise SceneRecipeError(
                f"unknown key '{key}' in [[pane]] entry #{index + 1}; "
                f"recognised keys: {', '.join(_RECOGNISED_PANE)}"
            )
    fields: dict[str, str | None] = {}
    for key in _RECOGNISED_PANE:
        if key in table:
            fields[key] = _normalise(_require_str(table[key], key=f"pane.{key}"))
        else:
            fields[key] = None
    return Pane(**fields)


def load_scene(name: str) -> tuple[str | None, str | None, str | None, list[Pane]]:
    """Load ``<scenes_dir>/<name>.toml`` into ``launch_scene`` arguments.

    Returns ``(layout, tab_title, tab_accent, panes)``. Raises
    :class:`SceneRecipeError` on a bad name, missing file, malformed TOML, or any
    schema violation — all BEFORE the caller issues a single kitten call, so a
    bad recipe never leaves a half-built tab.
    """
    _guard_name(name)
    directory = scenes_dir()
    path = directory / f"{name}.toml"
    # Defensive: the resolved file must live directly in the scenes directory.
    if path.parent != directory:
        raise SceneRecipeError(f"invalid scene name {name!r}: escapes scenes directory")

    if not path.is_file():
        available = ", ".join(s.name for s in list_scenes()) or "(none)"
        raise SceneRecipeError(f"no scene named {name!r} in {directory}; available: {available}")

    try:
        with path.open("rb") as fh:
            data = cast("dict[str, object]", tomllib.load(fh))
    except tomllib.TOMLDecodeError as exc:
        raise SceneRecipeError(f"malformed scene file {path}: {exc}") from exc

    for key in data:
        if key not in _RECOGNISED_TOP:
            raise SceneRecipeError(
                f"unknown top-level key '{key}' in {path}; "
                f"recognised keys: {', '.join(_RECOGNISED_TOP)}"
            )

    layout = _normalise(_require_str(data["layout"], key="layout")) if "layout" in data else None
    tab_title = (
        _normalise(_require_str(data["tab_title"], key="tab_title"))
        if "tab_title" in data
        else None
    )
    tab_accent = (
        _normalise(_require_str(data["tab_accent"], key="tab_accent"))
        if "tab_accent" in data
        else None
    )

    raw_panes = data.get("pane")
    if raw_panes is None:
        raise SceneRecipeError(f"scene file {path} defines no [[pane]]; at least one is required")
    if not isinstance(raw_panes, list):
        raise SceneRecipeError(f"'pane' in {path} must be an array of tables ([[pane]])")
    pane_list = cast("list[object]", raw_panes)
    panes = [_build_pane(raw, index=i) for i, raw in enumerate(pane_list)]
    if not panes:
        raise SceneRecipeError(f"scene file {path} defines no [[pane]]; at least one is required")

    return layout, tab_title, tab_accent, panes


@dataclass(frozen=True)
class SceneSummary:
    """One row of ``my-kitty scene list`` output."""

    name: str
    tab_title: str | None = None
    pane_count: int | None = None
    error: str | None = None


def list_scenes() -> list[SceneSummary]:
    """Summarise every ``*.toml`` recipe in the scenes directory, sorted by name.

    A file that fails to parse or validate is included with its ``error`` set
    (never silently dropped). A missing or empty directory yields ``[]``.
    """
    directory = scenes_dir()
    if not directory.is_dir():
        return []
    summaries: list[SceneSummary] = []
    for path in sorted(directory.glob("*.toml")):
        name = path.stem
        try:
            _layout, tab_title, _accent, panes = load_scene(name)
        except SceneRecipeError as exc:
            summaries.append(SceneSummary(name=name, error=str(exc)))
            continue
        summaries.append(SceneSummary(name=name, tab_title=tab_title, pane_count=len(panes)))
    return summaries


def _display_width(text: str) -> int:
    """Approximate terminal cell width of ``text`` (dep-free).

    Counts East-Asian wide/fullwidth code points as 2 cells and skips zero-width
    combining marks. Good enough to align CJK and most emoji; a handful of emoji
    with ambiguous width may still nudge a column by one cell.
    """
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def _pad(text: str, width: int) -> str:
    """Left-justify ``text`` to ``width`` display cells."""
    return text + " " * max(0, width - _display_width(text))


def scene_name_completer(*, prefix: str = "", **_kwargs: object) -> list[str]:
    """argcomplete completer for the ``scene launch`` positional name.

    Globs ``*.toml`` stems in the scenes directory (no TOML parse, so a
    malformed recipe never breaks completion). Returns names matching ``prefix``.
    """
    directory = scenes_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.toml") if p.stem.startswith(prefix))


def cli_scene_list(args: argparse.Namespace) -> int:
    """CLI handler for ``my-kitty scene list``."""
    summaries = list_scenes()

    if getattr(args, "names", False):
        for summary in summaries:
            print(summary.name)
        return 0

    if not summaries:
        print(f"no scenes yet — add a recipe under {scenes_dir()}")
        return 0

    def tab_cell(s: SceneSummary) -> str:
        return s.tab_title if s.tab_title else "-"

    valid = [s for s in summaries if s.error is None]
    name_w = max([_display_width("NAME"), *(_display_width(s.name) for s in summaries)])
    tab_w = max([_display_width("TAB"), *(_display_width(tab_cell(s)) for s in valid)])

    print(f"{_pad('NAME', name_w)}  {_pad('TAB', tab_w)}  PANES")
    for s in summaries:
        if s.error is not None:
            print(f"{_pad(s.name, name_w)}  (malformed: {s.error})")
            continue
        print(f"{_pad(s.name, name_w)}  {_pad(tab_cell(s), tab_w)}  {s.pane_count}")
    return 0
