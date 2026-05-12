"""H11/H19 — tab-nav category after phase1-curated-bindings-revert-defaults.

After the revert: ``tab-nav.conf`` carries five redundant rebinds on kitty's
own tab-navigation chords (`ctrl+shift+right`, `left`, `.`, `,`, `q`). The
`]`/`[` -> tab-nav mapping was dropped; those chords return to kitty's
default `next_window`/`previous_window` and are restated as redundant
rebinds under `window-nav.conf`.

All five entries are reported under source ``tab-nav`` with
``redundant=True``, ``override_of=None``, no conflicts, no allow-list
entries required.

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
    "ctrl+shift+right": "next_tab",
    "ctrl+shift+left": "previous_tab",
    "ctrl+shift+.": "move_tab_forward",
    "ctrl+shift+,": "move_tab_backward",
    "ctrl+shift+q": "close_tab",
}


@pytest.fixture()
def tab_nav_scratch(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes the windowing + clear + tab-nav payloads."""
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in ("windowing.conf", "tab-nav.conf", "intentional-overrides.conf"):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    copy_clear_payload(payload_dir)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n"
        f"include {payload_dir / 'tab-nav.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_tab_nav_conf_carries_five_map_lines(tab_nav_conf: str) -> None:
    """``tab-nav.conf`` carries exactly the five expected ``map`` lines."""
    map_lines = [
        line.strip() for line in tab_nav_conf.splitlines() if line.lstrip().startswith("map ")
    ]
    assert (
        len(map_lines) == 5
    ), f"expected exactly 5 map lines in tab-nav.conf, got {len(map_lines)}: {map_lines!r}"
    for chord, action in EXPECTED_ACTIONS.items():
        assert any(
            f"map {chord}" in line and line.endswith(action) for line in map_lines
        ), f"missing or wrong map line for {chord} -> {action} in {map_lines!r}"


def test_brackets_not_in_tab_nav(tab_nav_conf: str) -> None:
    """The legacy `]`/`[` -> tab-nav rebind has been dropped (D3)."""
    map_lines = [line for line in tab_nav_conf.splitlines() if line.lstrip().startswith("map ")]
    for forbidden in ("ctrl+shift+]", "ctrl+shift+["):
        leakage = [line for line in map_lines if forbidden in line]
        assert (
            leakage == []
        ), f"{forbidden} must no longer be a map line in tab-nav.conf; got {leakage}"


def test_introspection_reports_tab_nav_redundant(tab_nav_scratch: tuple[Path, Path]) -> None:
    """Each chord registers under ``tab-nav`` with ``redundant=True``."""
    conf_path, payload_dir = tab_nav_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    for chord, expected_action in EXPECTED_ACTIONS.items():
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert b.source == "tab-nav", f"{chord} should be tab-nav, got {b.source!r}"
        assert b.action == expected_action
        assert b.redundant is True, f"{chord} should be marked redundant; got {b!r}"
        assert b.override_of is None
        assert b.conflicts_with == ()

    tab_nav_entries = [b for b in report.bindings if b.source == "tab-nav"]
    assert len(tab_nav_entries) == 5
    assert report.conflicts_count == 0


def test_keys_json_exposes_tab_nav_section(tab_nav_scratch: tuple[Path, Path]) -> None:
    """``my-kitty keys --json`` payload carries five ``tab-nav`` entries, all redundant."""
    conf_path, payload_dir = tab_nav_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    payload = json.loads(report.to_json())

    tab_nav_entries = [b for b in payload["bindings"] if b["source"] == "tab-nav"]
    assert len(tab_nav_entries) == 5
    chords_to_actions = {b["chord"]: b["action"] for b in tab_nav_entries}
    assert chords_to_actions == EXPECTED_ACTIONS
    for b in tab_nav_entries:
        assert b["redundant"] is True
    assert payload["summary"]["conflicts"] == 0
