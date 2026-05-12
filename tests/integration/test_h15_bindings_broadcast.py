"""H15 — broadcast category (renumbered from h07 per the h11/h12/h13/h14 precedent).

Asserts:

* The promoted ``broadcast.conf`` carries one ``map`` line. The chord
  is genuinely new (probe finding h15, 2026-05-06: kitty 0.46.x has no
  default on ``ctrl+shift+i``), so it is not a redundant rebind nor an
  override of a kitty default. Matches design D6.
* ``binding_introspection.enumerate_bindings`` reports the chord under
  source ``broadcast`` with the expected action and ``override_of is
  None`` (no kitty-default shadow). It carries no ``conflicts_with``.
* ``my-kitty keys --json`` (via ``Report.to_json``) exposes a
  ``broadcast`` section with one entry and ``summary.conflicts == 0``.

Note: chord-driven keystrokes via ``send-key`` cannot exercise our key
bindings (kitty remote control injects key events without running them
through the keymap). The chord-to-action wiring is validated through the
binding-introspection module instead, which is the same mechanism backing
``my-kitty keys`` / the doctor's ``bindings`` check. Behavioural
confirmation that typing in the broadcast window mirrors to siblings
lives in the manual repro doc — the broadcast kitten reads interactive
input and the harness has no way to drive it.

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
    "ctrl+shift+i": "launch --allow-remote-control kitty +kitten broadcast",
}


@pytest.fixture()
def broadcast_conf() -> str:
    """Return the promoted ``config/kitty/broadcast.conf`` text."""
    return (PAYLOAD_SOURCE / "broadcast.conf").read_text()


@pytest.fixture()
def broadcast_scratch(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes our payload (with broadcast).

    Returns ``(conf_path, payload_dir)``. The conf file ``include``s the
    promoted ``windowing.conf``, ``clear.conf``, ``tab-nav.conf``,
    ``window-nav.conf``, ``font-zoom.conf``, ``detach.conf`` and
    ``broadcast.conf`` from the repo by absolute path; the payload dir
    contains those plus ``intentional-overrides.conf``.
    """
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (
        "windowing.conf",
        "tab-nav.conf",
        "window-nav.conf",
        "font-zoom.conf",
        "detach.conf",
        "broadcast.conf",
        "intentional-overrides.conf",
    ):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    copy_clear_payload(payload_dir)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n"
        f"include {payload_dir / 'tab-nav.conf'}\n"
        f"include {payload_dir / 'window-nav.conf'}\n"
        f"include {payload_dir / 'font-zoom.conf'}\n"
        f"include {payload_dir / 'detach.conf'}\n"
        f"include {payload_dir / 'broadcast.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_broadcast_conf_carries_one_map_line(broadcast_conf: str) -> None:
    """``broadcast.conf`` carries the one expected ``map`` line verbatim."""
    map_lines = [
        line.strip() for line in broadcast_conf.splitlines() if line.lstrip().startswith("map ")
    ]
    assert (
        len(map_lines) == 1
    ), f"expected exactly 1 map line in broadcast.conf, got {len(map_lines)}: {map_lines!r}"
    for chord, action in EXPECTED_ACTIONS.items():
        assert any(
            line.startswith(f"map {chord} ") and line.endswith(action) for line in map_lines
        ), f"missing or wrong map line for {chord} -> {action} in {map_lines!r}"


def test_introspection_reports_broadcast_section(broadcast_scratch: tuple[Path, Path]) -> None:
    """The chord registers under ``broadcast`` with the expected action.

    The chord is new (no kitty default shadow), so ``override_of`` is
    ``None`` and it carries no ``conflicts_with`` entry.
    """
    conf_path, payload_dir = broadcast_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    for chord, expected_action in EXPECTED_ACTIONS.items():
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert (
            b.source == "broadcast"
        ), f"{chord} should be attributed to broadcast, got {b.source!r}"
        assert (
            b.action == expected_action
        ), f"{chord} should be bound to {expected_action!r}, got {b.action!r}"
        assert b.override_of is None, (
            f"{chord} is a new binding (no kitty default on the chord); "
            f"override_of should be None, got {b.override_of!r}. If this fires, "
            f"a future kitty version added a default on the chord and the chord "
            f"now needs to be allow-listed in intentional-overrides.conf."
        )
        assert (
            b.conflicts_with == ()
        ), f"{chord} should not be flagged as a conflict; got {b.conflicts_with!r}"

    broadcast_entries = [b for b in report.bindings if b.source == "broadcast"]
    assert (
        len(broadcast_entries) == 1
    ), f"expected exactly 1 entry under source 'broadcast', got {len(broadcast_entries)}"
    assert (
        report.conflicts_count == 0
    ), f"expected 0 conflicts after broadcast category lands, got {report.conflicts_count}"


def test_keys_json_exposes_broadcast_section(broadcast_scratch: tuple[Path, Path]) -> None:
    """``my-kitty keys --json`` payload carries one ``broadcast`` entry."""
    conf_path, payload_dir = broadcast_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    payload = json.loads(report.to_json())

    broadcast_entries = [b for b in payload["bindings"] if b["source"] == "broadcast"]
    assert (
        len(broadcast_entries) == 1
    ), f"expected 1 broadcast entry in JSON output, got {len(broadcast_entries)}: {broadcast_entries!r}"
    chords_to_actions = {b["chord"]: b["action"] for b in broadcast_entries}
    assert (
        chords_to_actions == EXPECTED_ACTIONS
    ), f"broadcast JSON entries do not match expected mapping; got {chords_to_actions!r}"
    assert payload["summary"]["conflicts"] == 0
