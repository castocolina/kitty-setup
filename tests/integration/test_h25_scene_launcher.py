"""h25 — integration tests for the scene launcher (Phase 2 §12).

Promotes the green probe at ``tmp/h25-scene-launcher/run.py`` to the CI
surface. One named test per probe question Q1-Q5, plus one end-to-end test
that drives the shipped ``my-kitty scene launch`` CLI via subprocess.

Each test spawns ``kitty --start-as=minimized`` against a draft config that
includes the shipped ``config/kitty/layout.conf`` so the §11 mirrored Tall
list is loaded. Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from tests.integration._kitty_subprocess import (
    REPO_ROOT,
    draft_conf,
    get_color,
    kitten_call,
    ls,
    spawn_kitty,
    wait_for_socket,
)

LAYOUT_CONF: Path = REPO_ROOT / "config" / "kitty" / "layout.conf"
SETTLE_S: float = 0.4


def _draft_with_layout(scratch: Path) -> Path:
    """Draft kitty conf that includes remote-control.conf + the shipped layout.conf."""
    return draft_conf(
        scratch,
        extra_lines=(LAYOUT_CONF.read_text(encoding="utf-8").rstrip("\n"),),
    )


def _find_window_by_id(payload: list[dict], win_id: int) -> tuple[dict, dict] | None:
    for os_window in payload:
        for tab in os_window["tabs"]:
            for win in tab["windows"]:
                if win.get("id") == win_id:
                    return tab, win
    return None


def _get_text(socket: Path, win_id: int) -> str:
    result = kitten_call(socket, "get-text", "--match", f"id:{win_id}")
    if result.returncode != 0:
        return ""
    return result.stdout


def _new_window_id(stdout: str) -> int:
    """Parse ``int(stdout.strip())`` and assert the kitten returned a positive id."""
    raw = stdout.strip()
    assert raw.isdigit(), f"expected window id on stdout, got: {raw!r}"
    return int(raw)


# --------------------------------------------------------------------------- #
# Q1 — launch --type=tab combines tab-title + window-title + cwd + cmd
# --------------------------------------------------------------------------- #


def test_launch_tab_combines_tab_title_window_title_cwd_and_cmd_in_one_call(
    scratch_dir: Path,
) -> None:
    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        result = kitten_call(
            socket,
            "launch",
            "--type=tab",
            "--tab-title=h25-q1-tab",
            "--cwd=/tmp",
            "--title=h25-q1-win",
            "--hold",
            "bash",
            "-lc",
            "echo h25-q1-marker",
        )
        assert result.returncode == 0, f"launch failed: {result.stderr}"
        new_win_id = _new_window_id(result.stdout)
        assert new_win_id > 0

        time.sleep(SETTLE_S)
        payload = ls(socket)
        located = _find_window_by_id(payload, new_win_id)
        assert located is not None, "new window not found in ls"
        tab, win = located
        assert tab.get("title") == "h25-q1-tab"
        assert win.get("title") == "h25-q1-win"
        assert win.get("cwd") == "/tmp"
        assert "h25-q1-marker" in _get_text(socket, new_win_id)


# --------------------------------------------------------------------------- #
# Q2 — bare argv vs bash -lc vs compound `;` all reach the pane
# --------------------------------------------------------------------------- #


def test_startup_command_accepts_bare_argv_bash_lc_and_compound_shell(
    scratch_dir: Path,
) -> None:
    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        cases = [
            (["echo", "h25-q2a-marker"], ["h25-q2a-marker"]),
            (["bash", "-lc", "echo h25-q2b-marker"], ["h25-q2b-marker"]),
            (
                ["bash", "-lc", "echo h25-q2c1; echo h25-q2c2"],
                ["h25-q2c1", "h25-q2c2"],
            ),
        ]
        for argv, markers in cases:
            result = kitten_call(
                socket, "launch", "--type=window", "--hold", *argv
            )
            assert result.returncode == 0
            win_id = _new_window_id(result.stdout)
            time.sleep(SETTLE_S)
            text = _get_text(socket, win_id)
            for marker in markers:
                assert marker in text, f"marker {marker!r} missing from pane text"


# --------------------------------------------------------------------------- #
# Q3 — stdout = window id; --no-response is empty; --match recent:0 still lands
# --------------------------------------------------------------------------- #


def test_launch_stdout_is_window_id_and_recent_zero_still_targets_after_no_response(
    scratch_dir: Path,
) -> None:
    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        # Bare window launch — stdout is a positive int.
        result_win = kitten_call(
            socket, "launch", "--type=window", "--hold", "bash", "-lc", "true"
        )
        assert result_win.stdout.strip().isdigit()

        # Tab launch — the returned id is a WINDOW id, not a tab id.
        result_tab = kitten_call(
            socket, "launch", "--type=tab", "--hold", "bash", "-lc", "true"
        )
        returned_id = _new_window_id(result_tab.stdout)
        time.sleep(SETTLE_S)
        payload = ls(socket)
        assert _find_window_by_id(payload, returned_id) is not None, (
            "returned id should match a window id"
        )
        tab_ids = {tab.get("id") for os_w in payload for tab in os_w["tabs"]}
        assert returned_id not in tab_ids, (
            "returned id must NOT match a tab id (h25 Q3b finding)"
        )

        # --no-response suppresses stdout.
        result_nr = kitten_call(
            socket,
            "launch",
            "--type=window",
            "--no-response",
            "--hold",
            "bash",
            "-lc",
            "true",
        )
        assert result_nr.returncode == 0
        assert result_nr.stdout.strip() == ""

        # After --no-response, --match recent:0 still routes correctly.
        time.sleep(SETTLE_S)
        match_result = kitten_call(
            socket, "set-window-title", "--match", "recent:0", "h25-q3d-recent0"
        )
        assert match_result.returncode == 0
        time.sleep(SETTLE_S)
        payload = ls(socket)
        titles = [
            w.get("title")
            for os_w in payload
            for tab in os_w["tabs"]
            for w in tab["windows"]
        ]
        assert "h25-q3d-recent0" in titles


# --------------------------------------------------------------------------- #
# Q4 — subsequent window launches land in the new tab race-free
# --------------------------------------------------------------------------- #


def test_new_tab_focuses_synchronously_subsequent_window_launches_land_in_new_tab(
    scratch_dir: Path,
) -> None:
    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        pre = ls(socket)
        tab_ids_before = {tab["id"] for os_w in pre for tab in os_w["tabs"]}

        result_tab = kitten_call(
            socket,
            "launch",
            "--type=tab",
            "--tab-title=h25-q4-tab",
            "--hold",
            "bash",
            "-lc",
            "true",
        )
        assert result_tab.returncode == 0
        time.sleep(SETTLE_S)

        # Immediately fire two bare --type=window calls — no --match.
        result_w1 = kitten_call(
            socket, "launch", "--type=window", "--hold", "bash", "-lc", "true"
        )
        result_w2 = kitten_call(
            socket, "launch", "--type=window", "--hold", "bash", "-lc", "true"
        )
        assert result_w1.returncode == 0
        assert result_w2.returncode == 0
        time.sleep(SETTLE_S)

        post = ls(socket)
        new_tabs = [
            tab
            for os_w in post
            for tab in os_w["tabs"]
            if tab["id"] not in tab_ids_before
        ]
        assert len(new_tabs) == 1, "exactly one new tab expected"
        new_tab = new_tabs[0]
        assert len(new_tab["windows"]) == 3, (
            "new tab should contain 1 launch-tab + 2 launch-window panes"
        )
        old_tabs = [
            tab
            for os_w in post
            for tab in os_w["tabs"]
            if tab["id"] in tab_ids_before
        ]
        assert len(old_tabs) == len(tab_ids_before), "old tab count unchanged"


# --------------------------------------------------------------------------- #
# Q5 — full 3-pane scene: 6 calls, mirrored Tall, 3 distinct titles
# --------------------------------------------------------------------------- #


def test_three_pane_scene_takes_six_kitten_calls_with_mirrored_tall_and_distinct_titles(
    scratch_dir: Path,
) -> None:
    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        pre = ls(socket)
        tab_ids_before = {tab["id"] for os_w in pre for tab in os_w["tabs"]}

        call_count = 0
        result = kitten_call(
            socket,
            "launch",
            "--type=tab",
            "--tab-title=h25-q5-mon",
            "--title=h25-q5-p1",
            "--hold",
            "bash",
            "-lc",
            "echo h25-q5-p1",
        )
        call_count += 1
        assert result.returncode == 0
        _new_window_id(result.stdout)  # validate stdout shape

        kitten_call(socket, "goto-layout", "tall:mirrored=true")
        call_count += 1

        result = kitten_call(
            socket,
            "launch",
            "--type=window",
            "--title=h25-q5-p2",
            "--hold",
            "bash",
            "-lc",
            "echo h25-q5-p2",
        )
        call_count += 1
        p2_id = _new_window_id(result.stdout)

        kitten_call(
            socket,
            "set-colors",
            "--match",
            f"id:{p2_id}",
            "background=#001f3f",
        )
        call_count += 1

        result = kitten_call(
            socket,
            "launch",
            "--type=window",
            "--title=h25-q5-p3",
            "--hold",
            "bash",
            "-lc",
            "echo h25-q5-p3",
        )
        call_count += 1
        _new_window_id(result.stdout)

        accent_result = kitten_call(
            socket,
            "set-tab-color",
            "--match",
            "recent:0",
            "active_bg=#ff851b",
            "inactive_bg=#ff851b",
        )
        # Observable, not just exit-code: `active=` alone raised
        # "active is not a valid color name". Assert the real call lands.
        assert accent_result.returncode == 0, (
            f"set-tab-color failed: {accent_result.stderr!r}"
        )
        call_count += 1

        assert call_count == 6  # mirrors h25 Q5_kitten_call_count

        time.sleep(SETTLE_S * 2)
        payload = ls(socket)
        new_tabs = [
            tab
            for os_w in payload
            for tab in os_w["tabs"]
            if tab["id"] not in tab_ids_before
        ]
        assert len(new_tabs) == 1
        new_tab = new_tabs[0]
        assert len(new_tab["windows"]) == 3
        assert new_tab.get("title") == "h25-q5-mon"
        assert new_tab.get("layout_opts", {}).get("mirrored") == "y"
        titles = [w.get("title") for w in new_tab["windows"]]
        for expected in ("h25-q5-p1", "h25-q5-p2", "h25-q5-p3"):
            assert expected in titles, f"title {expected!r} missing"


# --------------------------------------------------------------------------- #
# End-to-end CLI — `my-kitty scene launch` via subprocess
# --------------------------------------------------------------------------- #


def test_my_kitty_scene_launch_cli_creates_three_pane_tab(
    scratch_dir: Path,
) -> None:
    conf = _draft_with_layout(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)

        pre = ls(socket)
        tab_ids_before = {tab["id"] for os_w in pre for tab in os_w["tabs"]}

        # `pin_pgrep_to_pid` is in-process only; subprocess'd my-kitty cannot
        # see the monkeypatch. Pass KITTY_LISTEN_ON in env so the child's
        # _resolve_socket short-circuits to the right instance directly.
        env = dict(os.environ)
        env["KITTY_LISTEN_ON"] = f"unix:{socket}"
        # Run from inside a kitty window, the child would inherit that window's id, take the
        # fill-current-tab branch (launcher.launch_scene), and fail the new-tab assertions.
        env.pop("KITTY_WINDOW_ID", None)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "kitty_setup.cli",
                "scene",
                "launch",
                "--layout=tall:mirrored=true",
                "--tab-title=h25e2e",
                "--tab-accent=#ff851b",
                "--pane",
                "title=p1,cmd=echo p1",
                "--pane",
                "title=p2,bg=#001f3f,cmd=echo p2",
                "--pane",
                "title=p3",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env=env,
        )
        assert result.returncode == 0, (
            f"my-kitty scene launch failed (rc={result.returncode}); "
            f"stderr={result.stderr!r}"
        )

        time.sleep(SETTLE_S * 2)
        payload = ls(socket)
        new_tabs = [
            tab
            for os_w in payload
            for tab in os_w["tabs"]
            if tab["id"] not in tab_ids_before
        ]
        assert len(new_tabs) == 1
        new_tab = new_tabs[0]
        assert new_tab.get("title") == "h25e2e"
        assert new_tab.get("layout_opts", {}).get("mirrored") == "y"

        titles = [w.get("title") for w in new_tab["windows"]]
        assert titles == ["p1", "p2", "p3"], (
            f"expected ordered titles [p1, p2, p3], got {titles}"
        )

        p2_id = next(
            w["id"] for w in new_tab["windows"] if w.get("title") == "p2"
        )
        p2_bg = get_color(socket, "background", match=f"id:{p2_id}")
        assert p2_bg is not None
        assert p2_bg.lower() == "#001f3f", (
            f"p2 background expected #001f3f, got {p2_bg!r}"
        )
