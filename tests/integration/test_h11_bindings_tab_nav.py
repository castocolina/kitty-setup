"""H11 — tab-nav category (renumbered from h03; h03 is taken by introspection).

Asserts:

* The promoted ``tab-nav.conf`` carries five ``map`` lines, one per chord. For
  three chords (``.``, ``,``, ``q``) the action matches the kitty default
  (redundant rebind for categorisation per design D5/D6); for ``]``/``[`` the
  action (``next_tab``/``previous_tab``) replaces kitty's default
  ``next_window``/``previous_window``.
* ``binding_introspection.enumerate_bindings`` reports each chord under source
  ``tab-nav`` with the expected action and ``override_of`` set to the kitty
  default action being shadowed — for three chords that default action equals
  the tab-nav action; for ``]``/``[`` it differs (``next_window``/
  ``previous_window`` vs. ``next_tab``/``previous_tab``). All five are
  allow-listed in ``intentional-overrides.conf`` and report no
  ``conflicts_with``.
* ``my-kitty keys --json`` (via ``Report.to_json``) exposes a ``tab-nav``
  section with five entries and ``summary.conflicts == 0``.

Note: chord-driven keystrokes via ``send-key`` cannot exercise our key
bindings (kitty remote control injects key events without running them
through the keymap). The chord-to-action wiring is validated through the
binding-introspection module instead, which is the same mechanism backing
``my-kitty keys`` / the doctor's ``bindings`` check.

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from kitty_setup import binding_introspection as bi

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_SOURCE = REPO_ROOT / "config" / "kitty"

EXPECTED_ACTIONS: dict[str, str] = {
    "ctrl+shift+]": "next_tab",
    "ctrl+shift+[": "previous_tab",
    "ctrl+shift+.": "move_tab_forward",
    "ctrl+shift+,": "move_tab_backward",
    "ctrl+shift+q": "close_tab",
}

# Action that the kitty default fires on the same chord. For three chords this
# matches our action (true redundant rebind). For ctrl+shift+]/[ the kitty
# default action is next_window/previous_window, so our binding genuinely
# changes behaviour — those chords belong to tab-nav (window-nav lands on
# vim-style hjkl in §4). All five remain allow-listed.
EXPECTED_OVERRIDE_OF: dict[str, str] = {
    "ctrl+shift+]": "next_window",
    "ctrl+shift+[": "previous_window",
    "ctrl+shift+.": "move_tab_forward",
    "ctrl+shift+,": "move_tab_backward",
    "ctrl+shift+q": "close_tab",
}


@pytest.fixture()
def tab_nav_scratch(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes our payload (with tab-nav).

    Returns ``(conf_path, payload_dir)``. The conf file ``include``s the
    promoted ``windowing.conf``, ``clear.conf`` and ``tab-nav.conf`` from the
    repo by absolute path; the payload dir contains those plus
    ``intentional-overrides.conf``.
    """
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (
        "windowing.conf",
        "clear.conf",
        "tab-nav.conf",
        "intentional-overrides.conf",
    ):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n"
        f"include {payload_dir / 'tab-nav.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_tab_nav_conf_carries_five_map_lines(tab_nav_conf: str) -> None:
    """``tab-nav.conf`` carries the five expected ``map`` lines verbatim."""
    map_lines = [
        line.strip()
        for line in tab_nav_conf.splitlines()
        if line.lstrip().startswith("map ")
    ]
    assert len(map_lines) == 5, (
        f"expected exactly 5 map lines in tab-nav.conf, got {len(map_lines)}: {map_lines!r}"
    )
    for chord, action in EXPECTED_ACTIONS.items():
        assert any(line.startswith(f"map {chord} ") and line.endswith(action) for line in map_lines), (
            f"missing or wrong map line for {chord} → {action} in {map_lines!r}"
        )


def test_introspection_reports_tab_nav_section(tab_nav_scratch: tuple[Path, Path]) -> None:
    """Each chord registers under ``tab-nav`` with the expected action."""
    conf_path, payload_dir = tab_nav_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    for chord, expected_action in EXPECTED_ACTIONS.items():
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert b.source == "tab-nav", (
            f"{chord} should be attributed to tab-nav, got {b.source!r}"
        )
        assert b.action == expected_action, (
            f"{chord} should be bound to {expected_action!r}, got {b.action!r}"
        )
        expected_override = EXPECTED_OVERRIDE_OF[chord]
        assert b.override_of == expected_override, (
            f"{chord} should override kitty default action {expected_override!r}; "
            f"got override_of={b.override_of!r}"
        )
        assert b.conflicts_with == (), (
            f"{chord} is allow-listed; should not be flagged as conflict, "
            f"got {b.conflicts_with!r}"
        )

    tab_nav_entries = [b for b in report.bindings if b.source == "tab-nav"]
    assert len(tab_nav_entries) == 5, (
        f"expected exactly 5 entries under source 'tab-nav', got {len(tab_nav_entries)}"
    )
    assert report.conflicts_count == 0, (
        f"expected 0 conflicts after tab-nav category lands, got {report.conflicts_count}"
    )


def test_keys_json_exposes_tab_nav_section(tab_nav_scratch: tuple[Path, Path]) -> None:
    """``my-kitty keys --json`` payload carries five ``tab-nav`` entries."""
    conf_path, payload_dir = tab_nav_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    payload = json.loads(report.to_json())

    tab_nav_entries = [b for b in payload["bindings"] if b["source"] == "tab-nav"]
    assert len(tab_nav_entries) == 5, (
        f"expected 5 tab-nav entries in JSON output, got {len(tab_nav_entries)}: {tab_nav_entries!r}"
    )
    chords_to_actions = {b["chord"]: b["action"] for b in tab_nav_entries}
    assert chords_to_actions == EXPECTED_ACTIONS, (
        f"tab-nav JSON entries do not match expected mapping; got {chords_to_actions!r}"
    )
    assert payload["summary"]["conflicts"] == 0
