"""H12/H19 — window-nav category after phase1-curated-bindings-revert-defaults.

After the revert: ``window-nav.conf`` carries four ``map`` lines, each a
redundant rebind of a kitty 0.46.x default. The vim-style hjkl mapping is
gone (the chords return to kitty's `show_scrollback`, `scroll_line_down`,
`scroll_line_up`, `next_layout`); the `f` rebind to `next_window` is gone
(reverts to kitty's `move_window_forward`). All four entries that remain
are reported under source ``window-nav`` with ``redundant=True``,
``override_of=None``, no conflicts, and no allow-list entries required.

The legacy h12 hjkl assertions live in
``tests/integration/test_h19_bindings_revert.py``; this file's purpose is
to lock in the new redundant-rebind shape.

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from kitty_setup import binding_introspection as bi
from tests.integration._helpers import copy_clear_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_SOURCE = REPO_ROOT / "config" / "kitty"

EXPECTED_ACTIONS: dict[str, str] = {
    "ctrl+shift+]": "next_window",
    "ctrl+shift+[": "previous_window",
    "ctrl+shift+f": "move_window_forward",
    "ctrl+shift+w": "close_window",
}


@pytest.fixture()
def window_nav_scratch(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes the catalog (with window-nav)."""
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (
        "windowing.conf",
        "tab-nav.conf",
        "window-nav.conf",
        "intentional-overrides.conf",
    ):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    copy_clear_payload(payload_dir)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n"
        f"include {payload_dir / 'tab-nav.conf'}\n"
        f"include {payload_dir / 'window-nav.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_window_nav_conf_carries_four_map_lines(window_nav_conf: str) -> None:
    """``window-nav.conf`` carries exactly four ``map`` lines."""
    map_lines = [
        line.strip() for line in window_nav_conf.splitlines() if line.lstrip().startswith("map ")
    ]
    assert (
        len(map_lines) == 4
    ), f"expected exactly 4 map lines in window-nav.conf, got {len(map_lines)}: {map_lines!r}"
    for chord, action in EXPECTED_ACTIONS.items():
        assert any(
            f"map {chord}" in line and line.endswith(action) for line in map_lines
        ), f"missing or wrong map line for {chord} -> {action} in {map_lines!r}"


def test_introspection_reports_window_nav_redundant(window_nav_scratch: tuple[Path, Path]) -> None:
    """Each chord registers under ``window-nav`` with ``redundant=True``."""
    conf_path, payload_dir = window_nav_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    for chord, expected_action in EXPECTED_ACTIONS.items():
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert (
            b.source == "window-nav"
        ), f"{chord} should be attributed to window-nav, got {b.source!r}"
        assert (
            b.action == expected_action
        ), f"{chord} should be bound to {expected_action!r}, got {b.action!r}"
        assert (
            b.redundant is True
        ), f"{chord} should be marked redundant (same action as kitty default), got {b!r}"
        assert (
            b.override_of is None
        ), f"{chord} is a redundant rebind, not an override; got override_of={b.override_of!r}"
        assert (
            b.conflicts_with == ()
        ), f"{chord} is redundant; should not be flagged as conflict, got {b.conflicts_with!r}"

    window_nav_entries = [b for b in report.bindings if b.source == "window-nav"]
    assert (
        len(window_nav_entries) == 4
    ), f"expected exactly 4 entries under source 'window-nav', got {len(window_nav_entries)}"
    assert (
        report.conflicts_count == 0
    ), f"expected 0 conflicts after window-nav revert, got {report.conflicts_count}"


def test_keys_json_exposes_window_nav_section(window_nav_scratch: tuple[Path, Path]) -> None:
    """``my-kitty keys --json`` payload carries four ``window-nav`` entries."""
    conf_path, payload_dir = window_nav_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    payload = json.loads(report.to_json())

    window_nav_entries = [b for b in payload["bindings"] if b["source"] == "window-nav"]
    assert len(window_nav_entries) == 4, (
        f"expected 4 window-nav entries in JSON output, got "
        f"{len(window_nav_entries)}: {window_nav_entries!r}"
    )
    chords_to_actions = {b["chord"]: b["action"] for b in window_nav_entries}
    assert (
        chords_to_actions == EXPECTED_ACTIONS
    ), f"window-nav JSON entries do not match expected mapping; got {chords_to_actions!r}"
    for b in window_nav_entries:
        assert b["redundant"] is True
    assert payload["summary"]["conflicts"] == 0
