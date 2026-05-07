"""H12 — window-nav category (renumbered from h04 per the h11 precedent).

Asserts:

* The promoted ``window-nav.conf`` carries six ``map`` lines, one per
  chord. For five chords (``h``, ``j``, ``k``, ``l``, ``f``) the action
  REPLACES the kitty default (``show_scrollback``, ``scroll_line_down``,
  ``scroll_line_up``, ``next_layout``, ``move_window_forward``); for one
  (``w``) the action matches the kitty default ``close_window`` (redundant
  rebind for categorisation per design D5/D6).
* ``binding_introspection.enumerate_bindings`` reports each chord under
  source ``window-nav`` with the expected action and ``override_of`` set to
  the kitty default action being shadowed. All six are allow-listed in
  ``intentional-overrides.conf`` and report no ``conflicts_with``.
* ``my-kitty keys --json`` (via ``Report.to_json``) exposes a
  ``window-nav`` section with six entries and ``summary.conflicts == 0``.

Note: chord-driven keystrokes via ``send-key`` cannot exercise our key
bindings (kitty remote control injects key events without running them
through the keymap). The chord-to-action wiring is validated through the
binding-introspection module instead, which is the same mechanism backing
``my-kitty keys`` / the doctor's ``bindings`` check. Behavioural
verification of `neighboring_window` lives in the manual repro doc.

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
    "ctrl+shift+h": "neighboring_window left",
    "ctrl+shift+j": "neighboring_window down",
    "ctrl+shift+k": "neighboring_window up",
    "ctrl+shift+l": "neighboring_window right",
    "ctrl+shift+w": "close_window",
    "ctrl+shift+f": "next_window",
}

# Action that the kitty default fires on the same chord. For five chords this
# differs from our action (genuine behaviour change); for ctrl+shift+w it
# matches our action (true redundant rebind). All six remain allow-listed.
# Probe finding (h12, 2026-05-06): design.md D6 listed h/j/k/l as "new" but
# kitty 0.46.x has defaults on every one of them — see the repro doc.
EXPECTED_OVERRIDE_OF: dict[str, str] = {
    "ctrl+shift+h": "show_scrollback",
    "ctrl+shift+j": "scroll_line_down",
    "ctrl+shift+k": "scroll_line_up",
    "ctrl+shift+l": "next_layout",
    "ctrl+shift+w": "close_window",
    "ctrl+shift+f": "move_window_forward",
}


@pytest.fixture()
def window_nav_scratch(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes our payload (with window-nav).

    Returns ``(conf_path, payload_dir)``. The conf file ``include``s the
    promoted ``windowing.conf``, ``clear.conf``, ``tab-nav.conf`` and
    ``window-nav.conf`` from the repo by absolute path; the payload dir
    contains those plus ``intentional-overrides.conf``.
    """
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (
        "windowing.conf",
        "clear.conf",
        "tab-nav.conf",
        "window-nav.conf",
        "intentional-overrides.conf",
    ):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n"
        f"include {payload_dir / 'tab-nav.conf'}\n"
        f"include {payload_dir / 'window-nav.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_window_nav_conf_carries_six_map_lines(window_nav_conf: str) -> None:
    """``window-nav.conf`` carries the six expected ``map`` lines verbatim."""
    map_lines = [
        line.strip()
        for line in window_nav_conf.splitlines()
        if line.lstrip().startswith("map ")
    ]
    assert len(map_lines) == 6, (
        f"expected exactly 6 map lines in window-nav.conf, got {len(map_lines)}: {map_lines!r}"
    )
    for chord, action in EXPECTED_ACTIONS.items():
        assert any(line.startswith(f"map {chord} ") and line.endswith(action) for line in map_lines), (
            f"missing or wrong map line for {chord} → {action} in {map_lines!r}"
        )


def test_introspection_reports_window_nav_section(window_nav_scratch: tuple[Path, Path]) -> None:
    """Each chord registers under ``window-nav`` with the expected action."""
    conf_path, payload_dir = window_nav_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    for chord, expected_action in EXPECTED_ACTIONS.items():
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert b.source == "window-nav", (
            f"{chord} should be attributed to window-nav, got {b.source!r}"
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

    window_nav_entries = [b for b in report.bindings if b.source == "window-nav"]
    assert len(window_nav_entries) == 6, (
        f"expected exactly 6 entries under source 'window-nav', got {len(window_nav_entries)}"
    )
    assert report.conflicts_count == 0, (
        f"expected 0 conflicts after window-nav category lands, got {report.conflicts_count}"
    )


def test_keys_json_exposes_window_nav_section(window_nav_scratch: tuple[Path, Path]) -> None:
    """``my-kitty keys --json`` payload carries six ``window-nav`` entries."""
    conf_path, payload_dir = window_nav_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    payload = json.loads(report.to_json())

    window_nav_entries = [b for b in payload["bindings"] if b["source"] == "window-nav"]
    assert len(window_nav_entries) == 6, (
        f"expected 6 window-nav entries in JSON output, got {len(window_nav_entries)}: {window_nav_entries!r}"
    )
    chords_to_actions = {b["chord"]: b["action"] for b in window_nav_entries}
    assert chords_to_actions == EXPECTED_ACTIONS, (
        f"window-nav JSON entries do not match expected mapping; got {chords_to_actions!r}"
    )
    assert payload["summary"]["conflicts"] == 0
