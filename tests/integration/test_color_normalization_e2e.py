"""End-to-end integration for client-side color normalization (friendly-color-input).

Proves against a real kitty that:
  * a name kitty natively REJECTS (`teal`) now applies as `#008080` end-to-end,
  * a hashless hex (`001a33`) applies as `#001a33`,
  * a scene with an unrecognized color opens NO window (rejected client-side).

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from tests.integration._kitty_subprocess import (
    draft_conf,
    get_color,
    ls,
    spawn_kitty,
    wait_for_socket,
)

SETTLE_S: float = 0.4


def _run(socket: Path, *argv: str, xdg: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["KITTY_LISTEN_ON"] = f"unix:{socket}"
    env.pop("KITTY_WINDOW_ID", None)
    if xdg is not None:
        env["XDG_CONFIG_HOME"] = str(xdg)
    return subprocess.run(  # noqa: S603 — fixed argv; trusted test inputs
        [sys.executable, "-m", "kitty_setup.cli", *argv],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        env=env,
    )


def test_gap_name_applies_as_hex(scratch_dir: Path) -> None:
    conf = draft_conf(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)
        win = ls(socket)[0]["tabs"][0]["windows"][0]["id"]

        result = _run(socket, "window", "background", "teal")
        assert result.returncode == 0, result.stderr
        time.sleep(SETTLE_S)
        # kitty rejects the NAME 'teal'; my-kitty translated it to #008080 first.
        assert get_color(socket, "background", match=f"id:{win}") == "#008080"


def test_hashless_hex_applies(scratch_dir: Path) -> None:
    conf = draft_conf(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)
        win = ls(socket)[0]["tabs"][0]["windows"][0]["id"]

        result = _run(socket, "window", "background", "001a33")  # no leading '#'
        assert result.returncode == 0, result.stderr
        time.sleep(SETTLE_S)
        assert get_color(socket, "background", match=f"id:{win}") == "#001a33"


def test_bad_color_in_scene_opens_no_window(scratch_dir: Path, tmp_path: Path) -> None:
    xdg = tmp_path / "xdg"
    scenes = xdg / "kitty-setup" / "scenes"
    scenes.mkdir(parents=True)
    # A 2-pane scene whose SECOND pane carries an unrecognized color.
    (scenes / "bad.toml").write_text(
        'layout = "tall"\n'
        '[[pane]]\ntitle = "ok"\n\n'
        '[[pane]]\ntitle = "broken"\nbg = "notacolor"\n',
        encoding="utf-8",
    )

    conf = draft_conf(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)
        tabs_before = {t["id"] for w in ls(socket) for t in w["tabs"]}

        result = _run(socket, "scene", "launch", "bad", xdg=xdg)
        time.sleep(SETTLE_S)

        assert result.returncode != 0
        assert "not a recognized color" in result.stderr
        tabs_after = {t["id"] for w in ls(socket) for t in w["tabs"]}
        # Rejected before any kitten launch — no new tab/window appeared.
        assert tabs_after == tabs_before


def test_empty_colour_window_background_is_absent(scratch_dir: Path) -> None:
    # D-12 (02-06): an empty colour is absent — no kitten argument, exit 0, no error. Before
    # 02-06 `background=` reached the kitten: exit 1 "Error:  is not a valid color".
    conf = draft_conf(scratch_dir)
    with spawn_kitty(conf, scratch_dir) as pid:
        socket = wait_for_socket(pid)
        time.sleep(SETTLE_S)
        # The scratch kitty has one window; with no --match, get-colors and the command
        # both address it as the active window.
        before = get_color(socket, "background")
        assert before is not None

        result = _run(socket, "window", "background", "")
        assert result.returncode == 0, result.stderr
        assert result.stderr == ""
        time.sleep(SETTLE_S)
        assert get_color(socket, "background") == before
