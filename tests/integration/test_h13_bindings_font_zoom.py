"""H13 — font-zoom category (renumbered from h05 per the h11/h12 precedent).

Asserts:

* The promoted ``font-zoom.conf`` carries three ``map`` lines, one per
  chord. For two chords (``=`` and ``-``) the action matches the kitty
  default (redundant rebind for categorisation per design D5/D6); for
  ``0`` the action (``change_font_size all 0``) replaces kitty's default
  ``tenth_window`` (probe finding h13, 2026-05-06 — design.md D6
  originally said "kitty default", which was wrong; kitty 0.46.x maps
  reset to ``ctrl+shift+backspace``).
* ``binding_introspection.enumerate_bindings`` reports each chord under
  source ``font-zoom`` with the expected action and ``override_of`` set
  to the kitty default action being shadowed. All three are allow-listed
  in ``intentional-overrides.conf`` and report no ``conflicts_with``.
* ``my-kitty keys --json`` (via ``Report.to_json``) exposes a
  ``font-zoom`` section with three entries and ``summary.conflicts == 0``.
* ``ctrl+shift+-`` is attributed to source ``font-zoom`` — NOT
  ``windowing``. This is the load-bearing assertion for §2's
  hsplit-relocation collision fix: pre-§2 the chord was bound by
  ``windowing.conf`` to ``launch --location=hsplit ...``; §2 moved hsplit
  to ``ctrl+shift+/``, freeing this chord for font-zoom. Closes the
  ``fix-ctrl-shift-minus-collision`` follow-up named in the archived
  ``phase1-binding-introspection`` proposal.

Note: chord-driven keystrokes via ``send-key`` cannot exercise our key
bindings (kitty remote control injects key events without running them
through the keymap). The chord-to-action wiring is validated through the
binding-introspection module instead, which is the same mechanism backing
``my-kitty keys`` / the doctor's ``bindings`` check. Visible font-size
change lives in the manual repro doc.

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
    "ctrl+shift+=": "change_font_size all +2.0",
    "ctrl+shift+-": "change_font_size all -2.0",
    "ctrl+shift+0": "change_font_size all 0",
}

# Action that the kitty default fires on the same chord. For `=` and `-` this
# matches our action (true redundant rebind). For `0` the kitty default action
# is `tenth_window`, so our binding genuinely changes behaviour — we want
# `change_font_size all 0` (font reset) on the obvious chord. Probe finding
# (h13, 2026-05-06): design.md D6 listed `0` → `change_font_size all 0` as
# kitty default; kitty 0.46.x actually maps it to `tenth_window` and binds
# reset on `ctrl+shift+backspace`. All three remain allow-listed.
EXPECTED_OVERRIDE_OF: dict[str, str] = {
    "ctrl+shift+=": "change_font_size all +2.0",
    "ctrl+shift+-": "change_font_size all -2.0",
    "ctrl+shift+0": "tenth_window",
}


@pytest.fixture()
def font_zoom_conf() -> str:
    """Return the promoted ``config/kitty/font-zoom.conf`` text."""
    return (PAYLOAD_SOURCE / "font-zoom.conf").read_text()


@pytest.fixture()
def font_zoom_scratch(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes our payload (with font-zoom).

    Returns ``(conf_path, payload_dir)``. The conf file ``include``s the
    promoted ``windowing.conf``, ``clear.conf``, ``tab-nav.conf``,
    ``window-nav.conf`` and ``font-zoom.conf`` from the repo by absolute
    path; the payload dir contains those plus ``intentional-overrides.conf``.
    """
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (
        "windowing.conf",
        "clear.conf",
        "tab-nav.conf",
        "window-nav.conf",
        "font-zoom.conf",
        "intentional-overrides.conf",
    ):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n"
        f"include {payload_dir / 'tab-nav.conf'}\n"
        f"include {payload_dir / 'window-nav.conf'}\n"
        f"include {payload_dir / 'font-zoom.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_font_zoom_conf_carries_three_map_lines(font_zoom_conf: str) -> None:
    """``font-zoom.conf`` carries the three expected ``map`` lines verbatim."""
    map_lines = [
        line.strip()
        for line in font_zoom_conf.splitlines()
        if line.lstrip().startswith("map ")
    ]
    assert len(map_lines) == 3, (
        f"expected exactly 3 map lines in font-zoom.conf, got {len(map_lines)}: {map_lines!r}"
    )
    for chord, action in EXPECTED_ACTIONS.items():
        assert any(line.startswith(f"map {chord} ") and line.endswith(action) for line in map_lines), (
            f"missing or wrong map line for {chord} → {action} in {map_lines!r}"
        )


def test_introspection_reports_font_zoom_section(font_zoom_scratch: tuple[Path, Path]) -> None:
    """Each chord registers under ``font-zoom`` with the expected action.

    Includes the load-bearing §2 collision-closure assertion: ``ctrl+shift+-``
    must be attributed to ``font-zoom``, NOT ``windowing``.
    """
    conf_path, payload_dir = font_zoom_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    for chord, expected_action in EXPECTED_ACTIONS.items():
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert b.source == "font-zoom", (
            f"{chord} should be attributed to font-zoom, got {b.source!r}"
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

    # §2 collision-closure: ctrl+shift+- is now ours under font-zoom, NOT
    # under windowing (where it lived pre-§2 as the hsplit chord).
    minus = by_chord["ctrl+shift+-"]
    assert minus.source == "font-zoom", (
        f"§2 collision fix incomplete: ctrl+shift+- must be attributed to "
        f"font-zoom, got {minus.source!r}. Pre-§2 the chord was bound by "
        f"windowing.conf to launch --location=hsplit; §2 moved hsplit to "
        f"ctrl+shift+/ to free this chord. If this assertion fires, the "
        f"hsplit relocation regressed."
    )
    assert minus.source != "windowing", (
        "§2 collision fix incomplete: ctrl+shift+- still attributed to windowing"
    )

    font_zoom_entries = [b for b in report.bindings if b.source == "font-zoom"]
    assert len(font_zoom_entries) == 3, (
        f"expected exactly 3 entries under source 'font-zoom', got {len(font_zoom_entries)}"
    )
    assert report.conflicts_count == 0, (
        f"expected 0 conflicts after font-zoom category lands, got {report.conflicts_count}"
    )


def test_keys_json_exposes_font_zoom_section(font_zoom_scratch: tuple[Path, Path]) -> None:
    """``my-kitty keys --json`` payload carries three ``font-zoom`` entries."""
    conf_path, payload_dir = font_zoom_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    payload = json.loads(report.to_json())

    font_zoom_entries = [b for b in payload["bindings"] if b["source"] == "font-zoom"]
    assert len(font_zoom_entries) == 3, (
        f"expected 3 font-zoom entries in JSON output, got {len(font_zoom_entries)}: {font_zoom_entries!r}"
    )
    chords_to_actions = {b["chord"]: b["action"] for b in font_zoom_entries}
    assert chords_to_actions == EXPECTED_ACTIONS, (
        f"font-zoom JSON entries do not match expected mapping; got {chords_to_actions!r}"
    )
    assert payload["summary"]["conflicts"] == 0
