"""H13/H19 — font-zoom category after phase1-curated-bindings-revert-defaults.

After the revert: ``font-zoom.conf`` carries three redundant rebinds on
kitty's own font-size chords (`ctrl+shift+=`, `ctrl+shift+-`, and
`ctrl+shift+backspace`). The `ctrl+shift+0` -> font-reset override has been
dropped; `0` returns to kitty's default `tenth_window` and reset is on
`ctrl+shift+backspace` (kitty's own default chord).

All three entries are reported under source ``font-zoom`` with
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
    "ctrl+shift+=": "change_font_size all +2.0",
    "ctrl+shift+-": "change_font_size all -2.0",
    "ctrl+shift+backspace": "change_font_size all 0",
}


@pytest.fixture()
def font_zoom_conf() -> str:
    """Return the promoted ``config/kitty/font-zoom.conf`` text."""
    return (PAYLOAD_SOURCE / "font-zoom.conf").read_text()


@pytest.fixture()
def font_zoom_scratch(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes the catalog (with font-zoom)."""
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (
        "windowing.conf",
        "tab-nav.conf",
        "window-nav.conf",
        "font-zoom.conf",
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
        f"include {payload_dir / 'font-zoom.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_font_zoom_conf_carries_three_map_lines(font_zoom_conf: str) -> None:
    """``font-zoom.conf`` carries exactly the three expected ``map`` lines."""
    map_lines = [
        line.strip() for line in font_zoom_conf.splitlines() if line.lstrip().startswith("map ")
    ]
    assert (
        len(map_lines) == 3
    ), f"expected exactly 3 map lines in font-zoom.conf, got {len(map_lines)}: {map_lines!r}"
    for chord, action in EXPECTED_ACTIONS.items():
        assert any(
            f"map {chord}" in line and line.endswith(action) for line in map_lines
        ), f"missing or wrong map line for {chord} -> {action} in {map_lines!r}"


def test_zero_chord_not_in_font_zoom(font_zoom_conf: str) -> None:
    """The legacy ctrl+shift+0 -> font-reset rebind has been dropped (D4)."""
    map_lines = [line for line in font_zoom_conf.splitlines() if line.lstrip().startswith("map ")]
    leakage = [line for line in map_lines if "ctrl+shift+0" in line]
    assert (
        leakage == []
    ), f"ctrl+shift+0 must no longer be a map line in font-zoom.conf; got {leakage}"


def test_introspection_reports_font_zoom_redundant(font_zoom_scratch: tuple[Path, Path]) -> None:
    """Each chord registers under ``font-zoom`` with ``redundant=True``."""
    conf_path, payload_dir = font_zoom_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    for chord, expected_action in EXPECTED_ACTIONS.items():
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert b.source == "font-zoom", f"{chord} should be font-zoom, got {b.source!r}"
        assert b.action == expected_action
        assert b.redundant is True
        assert b.override_of is None
        assert b.conflicts_with == ()

    font_zoom_entries = [b for b in report.bindings if b.source == "font-zoom"]
    assert len(font_zoom_entries) == 3
    assert report.conflicts_count == 0


def test_keys_json_exposes_font_zoom_section(font_zoom_scratch: tuple[Path, Path]) -> None:
    """``my-kitty keys --json`` payload carries three ``font-zoom`` entries, all redundant."""
    conf_path, payload_dir = font_zoom_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    payload = json.loads(report.to_json())

    font_zoom_entries = [b for b in payload["bindings"] if b["source"] == "font-zoom"]
    assert len(font_zoom_entries) == 3
    chords_to_actions = {b["chord"]: b["action"] for b in font_zoom_entries}
    assert chords_to_actions == EXPECTED_ACTIONS
    for b in font_zoom_entries:
        assert b["redundant"] is True
    assert payload["summary"]["conflicts"] == 0
