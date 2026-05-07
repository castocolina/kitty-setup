"""H14 — detach category (renumbered from h06 per the h11/h12/h13 precedent).

Asserts:

* The promoted ``detach.conf`` carries two ``map`` lines, one per chord.
  Both chords are genuinely new (probe finding h14, 2026-05-06: kitty
  0.46.x has neither ``ctrl+shift+d`` nor ``ctrl+shift+alt+d`` bound by
  default), so neither is a redundant rebind nor an override of a kitty
  default. Matches design D6.
* ``binding_introspection.enumerate_bindings`` reports each chord under
  source ``detach`` with the expected action and ``override_of is None``
  (no kitty-default shadow). Neither carries ``conflicts_with``.
* ``my-kitty keys --json`` (via ``Report.to_json``) exposes a ``detach``
  section with two entries and ``summary.conflicts == 0``.

Note: chord-driven keystrokes via ``send-key`` cannot exercise our key
bindings (kitty remote control injects key events without running them
through the keymap). The chord-to-action wiring is validated through the
binding-introspection module instead, which is the same mechanism backing
``my-kitty keys`` / the doctor's ``bindings`` check. The interactive
``detach_window ask`` / ``detach_tab ask`` picker UX lives in the manual
repro doc — the harness has no way to drive an interactive picker.

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
    "ctrl+shift+d": "detach_window ask",
    "ctrl+shift+alt+d": "detach_tab ask",
}


@pytest.fixture()
def detach_conf() -> str:
    """Return the promoted ``config/kitty/detach.conf`` text."""
    return (PAYLOAD_SOURCE / "detach.conf").read_text()


@pytest.fixture()
def detach_scratch(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes our payload (with detach).

    Returns ``(conf_path, payload_dir)``. The conf file ``include``s the
    promoted ``windowing.conf``, ``clear.conf``, ``tab-nav.conf``,
    ``window-nav.conf``, ``font-zoom.conf`` and ``detach.conf`` from the
    repo by absolute path; the payload dir contains those plus
    ``intentional-overrides.conf``.
    """
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (
        "windowing.conf",
        "clear.conf",
        "tab-nav.conf",
        "window-nav.conf",
        "font-zoom.conf",
        "detach.conf",
        "intentional-overrides.conf",
    ):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n"
        f"include {payload_dir / 'tab-nav.conf'}\n"
        f"include {payload_dir / 'window-nav.conf'}\n"
        f"include {payload_dir / 'font-zoom.conf'}\n"
        f"include {payload_dir / 'detach.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_detach_conf_carries_two_map_lines(detach_conf: str) -> None:
    """``detach.conf`` carries the two expected ``map`` lines verbatim."""
    map_lines = [
        line.strip()
        for line in detach_conf.splitlines()
        if line.lstrip().startswith("map ")
    ]
    assert len(map_lines) == 2, (
        f"expected exactly 2 map lines in detach.conf, got {len(map_lines)}: {map_lines!r}"
    )
    for chord, action in EXPECTED_ACTIONS.items():
        assert any(line.startswith(f"map {chord} ") and line.endswith(action) for line in map_lines), (
            f"missing or wrong map line for {chord} -> {action} in {map_lines!r}"
        )


def test_introspection_reports_detach_section(detach_scratch: tuple[Path, Path]) -> None:
    """Each chord registers under ``detach`` with the expected action.

    Both chords are new (no kitty default shadow), so ``override_of`` is
    ``None`` and neither carries a ``conflicts_with`` entry.
    """
    conf_path, payload_dir = detach_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    for chord, expected_action in EXPECTED_ACTIONS.items():
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert b.source == "detach", (
            f"{chord} should be attributed to detach, got {b.source!r}"
        )
        assert b.action == expected_action, (
            f"{chord} should be bound to {expected_action!r}, got {b.action!r}"
        )
        assert b.override_of is None, (
            f"{chord} is a new binding (no kitty default on the chord); "
            f"override_of should be None, got {b.override_of!r}. If this fires, "
            f"a future kitty version added a default on the chord and the chord "
            f"now needs to be allow-listed in intentional-overrides.conf."
        )
        assert b.conflicts_with == (), (
            f"{chord} should not be flagged as a conflict; got {b.conflicts_with!r}"
        )

    detach_entries = [b for b in report.bindings if b.source == "detach"]
    assert len(detach_entries) == 2, (
        f"expected exactly 2 entries under source 'detach', got {len(detach_entries)}"
    )
    assert report.conflicts_count == 0, (
        f"expected 0 conflicts after detach category lands, got {report.conflicts_count}"
    )


def test_keys_json_exposes_detach_section(detach_scratch: tuple[Path, Path]) -> None:
    """``my-kitty keys --json`` payload carries two ``detach`` entries."""
    conf_path, payload_dir = detach_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    payload = json.loads(report.to_json())

    detach_entries = [b for b in payload["bindings"] if b["source"] == "detach"]
    assert len(detach_entries) == 2, (
        f"expected 2 detach entries in JSON output, got {len(detach_entries)}: {detach_entries!r}"
    )
    chords_to_actions = {b["chord"]: b["action"] for b in detach_entries}
    assert chords_to_actions == EXPECTED_ACTIONS, (
        f"detach JSON entries do not match expected mapping; got {chords_to_actions!r}"
    )
    assert payload["summary"]["conflicts"] == 0
