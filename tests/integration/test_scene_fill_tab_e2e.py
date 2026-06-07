"""Integration: a multi-pane scene fills the current tab ONLY when it is solo.

phase2-scene-polish #2. Regression for the "4 windows in one tab" bug: launching
a 3-pane scene from a tab that already holds 2 windows must open a NEW tab and
leave the original tab's 2 windows untouched (not pile up to 4). The solo case
(1-window tab) must still fill in place to 3 windows, no new tab.

Gated by `KITTI_INTEGRATION=1` per `tests/conftest.py`.
"""

from __future__ import annotations

import time

from kitty_setup.scenes import launcher
from tests.integration._kitty_subprocess import (
    draft_conf,
    kitten_call,
    ls,
    spawn_kitty,
    wait_for_socket,
)


def _tabs(socket) -> list[dict]:
    return [tab for osw in ls(socket) for tab in osw["tabs"]]


def _three_panes() -> list[launcher.Pane]:
    return [
        launcher.Pane(title="shell"),
        launcher.Pane(title="git"),
        launcher.Pane(title="watch"),
    ]


def test_nonsolo_tab_opens_new_tab(tmp_path) -> None:
    """A 3-pane scene from a tab with 2 windows opens a new tab (not 4 windows)."""
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)

        # Make the current tab hold TWO windows.
        launch = kitten_call(socket, "launch", "--type=window")
        assert launch.returncode == 0, launch.stderr
        origin = int(launch.stdout.strip())
        time.sleep(0.3)

        tabs_before = _tabs(socket)
        assert len(tabs_before) == 1
        assert len(tabs_before[0]["windows"]) == 2

        rc = launcher.launch_scene(
            layout="tall",
            tab_title="DEV",
            tab_accent=None,
            panes=_three_panes(),
            to=f"unix:{socket}",
            origin_window=origin,
        )
        assert rc == 0
        time.sleep(0.5)

        tabs_after = _tabs(socket)
        # A new tab appeared; the original tab still holds exactly its 2 windows.
        assert len(tabs_after) == 2, f"expected 2 tabs, got {len(tabs_after)}"
        original = next(t for t in tabs_after if {w["id"] for w in t["windows"]} >= {origin})
        assert len(original["windows"]) == 2, "original tab must NOT have grown to 4"
        new_tab = next(t for t in tabs_after if t is not original)
        assert len(new_tab["windows"]) == 3, "the scene's 3 panes live in the new tab"


def test_solo_tab_fills_in_place(tmp_path) -> None:
    """A 3-pane scene from a 1-window tab fills it to 3 windows, no new tab."""
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)

        tabs_before = _tabs(socket)
        assert len(tabs_before) == 1 and len(tabs_before[0]["windows"]) == 1
        origin = tabs_before[0]["windows"][0]["id"]

        rc = launcher.launch_scene(
            layout="tall",
            tab_title="DEV",
            tab_accent=None,
            panes=_three_panes(),
            to=f"unix:{socket}",
            origin_window=origin,
        )
        assert rc == 0
        time.sleep(0.5)

        tabs_after = _tabs(socket)
        assert len(tabs_after) == 1, "solo tab must be filled in place, no new tab"
        assert len(tabs_after[0]["windows"]) == 3, "the tab now holds the 3 scene panes"
