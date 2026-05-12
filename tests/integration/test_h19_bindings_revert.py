"""H19 — every chord released by phase1-curated-bindings-revert-defaults resolves
back to its kitty 0.46.x default action.

Asserts via ``binding_introspection.enumerate_bindings`` against a scratch
``kitty.conf`` that includes every payload file. The reverted chords listed
in ``EXPECTED_DEFAULTS`` MUST appear under ``source == kitty-default`` with
their kitty-default action; none of them MUST be attributed to one of our
sources. The report MUST have zero conflicts.

Probe-pinned (see
``tmp/probes/phase1-curated-bindings-revert-defaults/01-kitty-defaults.md``):
the action strings below are the kitty 0.46.2 defaults captured by parsing
an empty config.

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from kitty_setup import binding_introspection as bi
from tests.integration._helpers import copy_clear_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_SOURCE = REPO_ROOT / "config" / "kitty"

# Conf payload files (parsed by kitty). The full catalog is included so the
# assertions cover the deployed shape end-to-end.
INCLUDED_PAYLOADS: tuple[str, ...] = (
    "windowing.conf",
    "clear.conf",
    "tab-nav.conf",
    "window-nav.conf",
    "font-zoom.conf",
    "detach.conf",
    "broadcast.conf",
    "url-hints.conf",
)
METADATA_PAYLOADS: tuple[str, ...] = ("intentional-overrides.conf",)

# Chords released by this change. Each MUST resolve to the kitty-default
# action on the right-hand side. See design.md D1-D5.
EXPECTED_DEFAULTS: dict[str, str] = {
    "ctrl+shift+h": "show_scrollback",
    "ctrl+shift+j": "scroll_line_down",
    "ctrl+shift+k": "scroll_line_up",
    "ctrl+shift+l": "next_layout",
    "ctrl+shift+0": "tenth_window",
    "ctrl+shift+x": "scroll_to_prompt 1",
    "ctrl+shift+/": "search_scrollback",
}

# Chords that were dropped from windowing.conf entirely (D2). The chord may
# or may not be bound by kitty's default keymap on a given OS — the only
# invariant we assert is that the chord is NOT attributed to one of our
# sources.
DROPPED_CHORDS: tuple[str, ...] = ("ctrl+shift+\\",)


@pytest.fixture()
def scratch_config(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that `include`s every payload file."""
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (*INCLUDED_PAYLOADS, *METADATA_PAYLOADS):
        if name == "clear.conf":
            copy_clear_payload(payload_dir)
        else:
            shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        "".join(f"include {payload_dir / name}\n" for name in INCLUDED_PAYLOADS),
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_reverted_chords_resolve_to_kitty_defaults(scratch_config: tuple[Path, Path]) -> None:
    """Every chord in ``EXPECTED_DEFAULTS`` resolves to the kitty-default action."""
    conf_path, payload_dir = scratch_config
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    ours = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}
    defaults = {b.chord: b for b in report.bindings if b.source == bi.DEFAULT_SOURCE}

    for chord, expected_action in EXPECTED_DEFAULTS.items():
        assert chord not in ours, (
            f"{chord} must no longer be one of our bindings (revert regressed); "
            f"got {ours[chord]!r}"
        )
        assert chord in defaults, (
            f"{chord} expected under kitty defaults with action {expected_action!r}; "
            f"chord missing from default keymap entirely"
        )
        actual_action = defaults[chord].action
        assert (
            actual_action == expected_action
        ), f"{chord}: expected kitty default action {expected_action!r}, got {actual_action!r}"


def test_dropped_chords_are_not_ours(scratch_config: tuple[Path, Path]) -> None:
    """Chords removed from windowing.conf are not attributed to our sources."""
    conf_path, payload_dir = scratch_config
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    ours = {b.chord for b in report.bindings if b.source != bi.DEFAULT_SOURCE}
    for chord in DROPPED_CHORDS:
        assert (
            chord not in ours
        ), f"{chord} should not be one of our bindings any more (dropped by D2)"


def test_no_conflicts_after_revert(scratch_config: tuple[Path, Path]) -> None:
    """``Summary: 0 conflicts`` once the revert lands."""
    conf_path, payload_dir = scratch_config
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    assert report.conflicts_count == 0, (
        f"expected 0 conflicts after phase1-curated-bindings-revert-defaults; "
        f"got {report.conflicts_count}"
    )
