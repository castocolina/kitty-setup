"""End-to-end integration test for declarative scene recipes (Phase 2 §12 decl).

Drives the shipped ``my-kitty scene launch <name>`` against a freshly spawned
kitty, with the recipe authored as a temp TOML found via ``$XDG_CONFIG_HOME``.
Asserts the same tab/pane/bg observables as the h25 inline e2e test — proving
the declarative front-end materialises an identical scene through the unchanged
``launch_scene`` engine. Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from tests.integration._kitty_subprocess import (
    REPO_ROOT,
    draft_conf,
    get_color,
    ls,
    spawn_kitty,
    wait_for_socket,
)

LAYOUT_CONF: Path = REPO_ROOT / "config" / "kitty" / "layout.conf"
SETTLE_S: float = 0.4

RECIPE_BODY = """\
layout = "tall:mirrored=true"
tab_title = "recipe-e2e"

[[pane]]
title = "p1"
cmd = "echo p1"

[[pane]]
title = "p2"
bg = "#001f3f"
cmd = "echo p2"

[[pane]]
title = "p3"
"""


def _draft_with_layout(scratch: Path) -> Path:
    return draft_conf(
        scratch,
        extra_lines=(LAYOUT_CONF.read_text(encoding="utf-8").rstrip("\n"),),
    )


def test_my_kitty_scene_launch_named_recipe_creates_three_pane_tab(
    scratch_dir: Path,
    tmp_path: Path,
) -> None:
    # Author the recipe where the loader will look: $XDG_CONFIG_HOME/kitty-setup/scenes/.
    xdg = tmp_path / "xdg"
    scenes = xdg / "kitty-setup" / "scenes"
    scenes.mkdir(parents=True)
    (scenes / "demo.toml").write_text(RECIPE_BODY, encoding="utf-8")

    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        pre = ls(socket)
        tab_ids_before = {tab["id"] for os_w in pre for tab in os_w["tabs"]}

        # my-kitty runs in a separate process: pin the socket via env, and point
        # XDG_CONFIG_HOME at the temp config root so it finds demo.toml.
        env = dict(os.environ)
        env["KITTY_LISTEN_ON"] = f"unix:{socket}"
        env["XDG_CONFIG_HOME"] = str(xdg)
        # Run from inside a kitty window, the child would inherit that window's id, take the
        # fill-current-tab branch (launcher.launch_scene), and fail the new-tab assertions.
        env.pop("KITTY_WINDOW_ID", None)

        result = subprocess.run(
            [sys.executable, "-m", "kitty_setup.cli", "scene", "launch", "demo"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0, (
            f"my-kitty scene launch demo failed (rc={result.returncode}); "
            f"stderr={result.stderr!r}"
        )

        time.sleep(SETTLE_S * 2)
        payload = ls(socket)
        new_tabs = [
            tab for os_w in payload for tab in os_w["tabs"] if tab["id"] not in tab_ids_before
        ]
        assert len(new_tabs) == 1
        new_tab = new_tabs[0]
        assert new_tab.get("title") == "recipe-e2e"
        assert new_tab.get("layout_opts", {}).get("mirrored") == "y"

        titles = [w.get("title") for w in new_tab["windows"]]
        assert titles == ["p1", "p2", "p3"], f"expected ordered titles [p1, p2, p3], got {titles}"

        p2_id = next(w["id"] for w in new_tab["windows"] if w.get("title") == "p2")
        p2_bg = get_color(socket, "background", match=f"id:{p2_id}")
        assert p2_bg is not None
        assert p2_bg.lower() == "#001f3f", f"p2 background expected #001f3f, got {p2_bg!r}"


def _run_scene_launch(
    xdg: Path,
    socket: Path,
    name: str,
    *,
    cwd: Path | None = None,
    window_id: int | None = None,
) -> None:
    env = dict(os.environ)
    env["KITTY_LISTEN_ON"] = f"unix:{socket}"
    env["XDG_CONFIG_HOME"] = str(xdg)
    env.pop("KITTY_WINDOW_ID", None)
    if window_id is not None:
        # Simulate launching from inside that kitty window (fills the current tab).
        env["KITTY_WINDOW_ID"] = str(window_id)
    result = subprocess.run(  # noqa: S603 — fixed argv; `name` is a test-supplied scene stem
        [sys.executable, "-m", "kitty_setup.cli", "scene", "launch", name],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        env=env,
        cwd=str(cwd) if cwd is not None else None,
    )
    assert (
        result.returncode == 0
    ), f"scene launch {name} failed (rc={result.returncode}); stderr={result.stderr!r}"


def test_single_pane_scene_joins_current_tab(scratch_dir: Path, tmp_path: Path) -> None:
    xdg = tmp_path / "xdg"
    scenes = xdg / "kitty-setup" / "scenes"
    scenes.mkdir(parents=True)
    (scenes / "solo.toml").write_text('[[pane]]\ntitle = "lonely"\n', encoding="utf-8")

    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        pre = ls(socket)
        tab_ids_before = {tab["id"] for os_w in pre for tab in os_w["tabs"]}

        _run_scene_launch(xdg, socket, "solo")
        time.sleep(SETTLE_S * 2)

        payload = ls(socket)
        tab_ids_after = {tab["id"] for os_w in payload for tab in os_w["tabs"]}
        # No new tab was created — the lone window joined the existing tab.
        assert tab_ids_after == tab_ids_before, "single-pane scene must NOT create a new tab"
        all_titles = [
            w.get("title") for os_w in payload for tab in os_w["tabs"] for w in tab["windows"]
        ]
        assert "lonely" in all_titles


def test_scene_panes_inherit_launch_directory(scratch_dir: Path, tmp_path: Path) -> None:
    xdg = tmp_path / "xdg"
    scenes = xdg / "kitty-setup" / "scenes"
    scenes.mkdir(parents=True)
    (scenes / "where.toml").write_text('[[pane]]\ntitle = "here"\n', encoding="utf-8")

    launch_dir = tmp_path / "launchpoint"
    launch_dir.mkdir()

    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        _run_scene_launch(xdg, socket, "where", cwd=launch_dir)
        time.sleep(SETTLE_S * 2)

        payload = ls(socket)
        win = next(
            w
            for os_w in payload
            for tab in os_w["tabs"]
            for w in tab["windows"]
            if w.get("title") == "here"
        )
        # The pane set no cwd, so it inherits the directory the scene launched from.
        assert win.get("cwd") == str(
            launch_dir
        ), f"expected cwd {launch_dir}, got {win.get('cwd')!r}"


def test_multipane_scene_fills_current_tab_when_launched_inside_kitty(
    scratch_dir: Path, tmp_path: Path
) -> None:
    # Launched from inside kitty ($KITTY_WINDOW_ID set), a 3-pane scene must fill
    # the CURRENT tab (origin window reused as pane 0) — NOT open a new tab.
    xdg = tmp_path / "xdg"
    scenes = xdg / "kitty-setup" / "scenes"
    scenes.mkdir(parents=True)
    (scenes / "dev.toml").write_text(
        'layout = "tall"\n'
        'tab_title = "DEV"\n'
        'tab_accent = "#2ecc40"\n\n'
        '[[pane]]\ntitle = "shell"\n\n'
        '[[pane]]\ntitle = "git"\nbg = "#0b1f0b"\ncmd = "sleep 30"\n\n'
        '[[pane]]\ntitle = "watch"\ncmd = "sleep 30"\n',
        encoding="utf-8",
    )

    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        pre = ls(socket)
        tab_ids_before = {tab["id"] for os_w in pre for tab in os_w["tabs"]}
        origin_win = pre[0]["tabs"][0]["windows"][0]["id"]

        _run_scene_launch(xdg, socket, "dev", window_id=origin_win)
        time.sleep(SETTLE_S * 2)

        payload = ls(socket)
        tab_ids_after = {tab["id"] for os_w in payload for tab in os_w["tabs"]}
        assert (
            tab_ids_after == tab_ids_before
        ), "multi-pane scene must NOT create a new tab in-kitty"

        # The single tab now holds exactly the 3 scene panes (origin reused as pane 0).
        tab = payload[0]["tabs"][0]
        titles = [w.get("title") for w in tab["windows"]]
        assert titles == ["shell", "git", "watch"], titles
        assert tab.get("title") == "DEV"
        assert tab.get("layout") == "tall"
