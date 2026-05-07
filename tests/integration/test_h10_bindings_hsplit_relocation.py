"""H10 — horizontal-split chord moves from ctrl+shift+- to ctrl+shift+/.

Asserts:

* The promoted ``windowing.conf`` binds ``ctrl+shift+/`` to
  ``launch --location=hsplit --cwd=current`` and drops the old
  ``ctrl+shift+-`` map line entirely.
* The hsplit launch action still creates a new pane (the cwd-inheriting
  behaviour is unchanged; only the chord moved).
* ``binding_introspection.enumerate_bindings`` reports ``ctrl+shift+/`` under
  source ``windowing`` (allow-listed override of ``search_scrollback``) and
  ``ctrl+shift+-`` under ``kitty-default`` with action
  ``change_font_size all -2.0``.

Note: chord-driven keystrokes via ``send-key`` cannot exercise our key
bindings (kitty remote control injects key events without running them
through the keymap). The chord-to-action wiring is validated through the
binding-introspection module instead, which is the same mechanism backing
``my-kitty keys`` / the doctor's ``bindings`` check.

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from kitty_setup import binding_introspection as bi
from kitty_setup.harness.kitty_session import KittySession

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_SOURCE = REPO_ROOT / "config" / "kitty"

SETTLE_S = 0.5


def _window_count(session: KittySession) -> int:
    total = 0
    for os_window in session.ls():
        for tab in os_window.get("tabs", []):
            total += len(tab.get("windows", []))
    return total


def test_windowing_conf_binds_new_chord_and_drops_old(windowing_conf: str) -> None:
    """``windowing.conf`` binds hsplit on ``ctrl+shift+/`` and removes ``ctrl+shift+-``."""
    map_lines = [
        line.strip()
        for line in windowing_conf.splitlines()
        if line.lstrip().startswith("map ")
    ]
    assert any(
        "ctrl+shift+/" in line and "hsplit" in line for line in map_lines
    ), f"expected hsplit on ctrl+shift+/, got map lines:\n{map_lines!r}"
    assert not any(
        "ctrl+shift+-" in line for line in map_lines
    ), f"ctrl+shift+- must not be a map line in windowing.conf; got {map_lines!r}"


def test_hsplit_launch_action_still_creates_window(windowing_conf: str) -> None:
    """The hsplit ``launch`` action behind the chord still produces a new window.

    Exercises the action behaviour (the chord delivers exactly this launch
    invocation; chord traversal is verified separately via introspection).
    """
    with KittySession(config_snippets=[windowing_conf]) as session:
        time.sleep(SETTLE_S)
        before = _window_count(session)
        session.launch(location="hsplit", cwd="current")
        time.sleep(SETTLE_S)
        after = _window_count(session)
        assert after > before, (
            f"expected hsplit launch to add a window; before={before}, after={after}"
        )


def test_introspection_attributes_chords_correctly(tmp_path: Path) -> None:
    """``my-kitty keys`` reports the chord move correctly.

    * ``ctrl+shift+/`` is ours under ``windowing`` (allow-listed override of
      ``search_scrollback``).
    * ``ctrl+shift+-`` is no longer ours; it appears under ``kitty-default``
      with action ``change_font_size all -2.0``.
    * The report has zero conflicts.
    """
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in ("windowing.conf", "clear.conf", "intentional-overrides.conf"):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n",
        encoding="utf-8",
    )

    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    ours = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}
    defaults = {b.chord: b for b in report.bindings if b.source == bi.DEFAULT_SOURCE}

    assert "ctrl+shift+/" in ours, "ctrl+shift+/ missing from our bindings"
    hsplit = ours["ctrl+shift+/"]
    assert hsplit.source == "windowing"
    assert hsplit.action == "launch --location=hsplit --cwd=current"
    assert hsplit.override_of == "search_scrollback"
    assert hsplit.conflicts_with == ()

    assert "ctrl+shift+-" not in ours, (
        f"ctrl+shift+- must not be one of our bindings; got {ours.get('ctrl+shift+-')}"
    )
    assert "ctrl+shift+-" in defaults, "ctrl+shift+- expected under kitty defaults"
    minus = defaults["ctrl+shift+-"]
    assert "change_font_size" in minus.action and "-2.0" in minus.action, (
        f"expected change_font_size all -2.0 on ctrl+shift+-, got {minus.action!r}"
    )

    assert report.conflicts_count == 0, (
        f"expected 0 conflicts after the chord move, got {report.conflicts_count}"
    )
