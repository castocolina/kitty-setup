"""Integration: a multi-pane scene fills the current tab ONLY when it is solo (02-13 extends it).

phase2-scene-polish #2. Regression for the "4 windows in one tab" bug: launching
a 3-pane scene from a tab that already holds 2 windows must open a NEW tab and
leave the original tab's 2 windows untouched (not pile up to 4). The solo case
(1-window tab) must still fill in place to 3 windows, no new tab.

02-04 (R1.4) adds `fill_tab_quoting`: pane 0's `cwd` reaches the reused shell as
a `send-text` string, so only a real shell proves the quoting is the right quoting.
02-13 (WR-02, WR-03) replaces that quoting with the typeable rule: an untypeable pane 0
opens in a new tab, and pane 0's cwd means what every other pane's cwd means. The cases
for both are below, each in a real kitty.

Every case runs under `sandbox_fill_tab_home`, so none writes into the real HOME: bash
writes `$HOME/.bash_history` on exit and on SIGHUP, and fish creates `~/.cache/fish`,
`~/.config/fish` and `~/.local/share/fish` (both measured 2026-11-03).

Gated by `KITTI_INTEGRATION=1` per `tests/conftest.py`.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

import pytest

from kitty_setup.scenes import launcher
from tests.integration._kitty_subprocess import (
    draft_conf,
    kitten_call,
    spawn_kitty,
    wait_for_socket,
)


@pytest.fixture(autouse=True)
def sandbox_fill_tab_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point every case's HOME, XDG directories and HISTFILE at this module's own tmp_path.

    `sandbox_integration_home` (02-12) runs first and already sandboxes HOME, the XDG
    directories and HISTFILE. This layers the module's directory and an empty INPUTRC over it.
    The empty INPUTRC pins readline to its emacs defaults, so the Ctrl-A case is deterministic.
    """
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    for name, rel in (
        ("XDG_CONFIG_HOME", ".config"),
        ("XDG_DATA_HOME", ".local/share"),
        ("XDG_CACHE_HOME", ".cache"),
        ("XDG_STATE_HOME", ".local/state"),
    ):
        (home / rel).mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(name, str(home / rel))
    monkeypatch.setenv("HISTFILE", str(home / ".bash_history"))
    inputrc = tmp_path / "inputrc"
    inputrc.write_text("", encoding="utf-8")
    monkeypatch.setenv("INPUTRC", str(inputrc))


def _tabs(socket: Path) -> list[Any]:
    """Every tab of every OS window from `kitten @ ls`, typed Any (kitty owns the JSON)."""
    result = kitten_call(socket, "ls")
    assert result.returncode == 0, result.stderr
    tree: Any = json.loads(result.stdout)
    return [tab for osw in tree for tab in osw["tabs"]]


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


def _solo_window_and_cwd(socket: Path, window_id: int | None) -> tuple[int, str | None]:
    """Return (id, cwd) of ``window_id`` — or of the first window when ``None`` — per ``ls``."""
    result = kitten_call(socket, "ls")
    assert result.returncode == 0, result.stderr
    tree: Any = json.loads(result.stdout)
    for osw in tree:
        for tab in osw["tabs"]:
            for window in tab["windows"]:
                if window_id is None or window["id"] == window_id:
                    return int(window["id"]), window.get("cwd")
    raise AssertionError(f"window {window_id} not in kitten @ ls")


def test_fill_tab_quoting_space_and_metachar_in_pane0_cwd(tmp_path: Path) -> None:
    """Pane 0's cwd with a space and `;` is one `cd` argument; the `touch` never runs."""
    # Everything under this case's own tmp_path, never a fixed absolute path: a stale file from an
    # earlier run cannot decide the result. The unquoted payload
    # `cd <tmp>/my dir; touch <tmp>/PWNED` would create the sentinel; the directory whose
    # name carries that text exists, so the correctly quoted `cd` lands in it.
    sentinel = tmp_path / "PWNED"
    target = Path(f"{tmp_path}/my dir; touch {sentinel}")
    target.mkdir(parents=True)
    target = target.resolve()
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        origin, _ = _solo_window_and_cwd(socket, None)

        rc = launcher.launch_scene(
            None,
            None,
            None,
            [launcher.Pane(cwd=str(target)), launcher.Pane(title="p1")],
            to=f"unix:{socket}",
            origin_window=origin,
        )
        assert rc == 0

        cwd: str | None = None
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and not sentinel.exists():
            _, cwd = _solo_window_and_cwd(socket, origin)
            if cwd == str(target):
                break
            time.sleep(0.1)
        time.sleep(0.3)  # let anything typed after the `cd` finish before the verdict
        assert not sentinel.exists(), f"injected command ran: {sentinel} was created"
        assert cwd == str(target), f"reused window cwd {cwd!r}, expected {str(target)!r}"


def _origin_id(socket: Path) -> int:
    return int(_tabs(socket)[0]["windows"][0]["id"])


def _poll_absent(path: Path) -> None:
    """Poll for ``path`` every 0.1 s for 5 s; return early the moment it appears."""
    for _ in range(50):
        if path.exists():
            return
        time.sleep(0.1)


def _assert_falls_back(socket: Path, origin: int) -> None:
    """The argv path ran: a second tab opened, and the origin tab kept exactly its one window."""
    tabs = _tabs(socket)
    assert len(tabs) == 2, f"expected a second tab, got {len(tabs)}"
    origin_tab = next(t for t in tabs if any(w["id"] == origin for w in t["windows"]))
    assert len(origin_tab["windows"]) == 1, "the origin tab must keep exactly its one window"


def test_fill_tab_fish_injection_falls_back(tmp_path: Path) -> None:
    """A fish origin given the injection payload opens a new tab; the sentinel is never created."""
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("fish is not installed")
    sentinel = tmp_path / "PWNED"
    # Two backslashes before the quote. kitten decodes `\\` to `\`, so fish receives the `\'` that
    # shifts its quoting. A one-backslash value reaches fish as a plain quote and runs nothing.
    cwd = f"{tmp_path}/a\\\\'\"; touch {sentinel}; #"
    Path(cwd).mkdir(parents=True)
    conf = draft_conf(tmp_path, extra_lines=(f"shell {fish} --no-config --private",))
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        origin = _origin_id(socket)
        rc = launcher.launch_scene(
            None,
            None,
            None,
            [launcher.Pane(cwd=cwd), launcher.Pane(title="p1")],
            to=f"unix:{socket}",
            origin_window=origin,
        )
        assert rc == 0
        _poll_absent(sentinel)
        assert not sentinel.exists(), f"injected command ran (fish): {sentinel}"
        _assert_falls_back(socket, origin)


def test_fill_tab_escape_sequence_falls_back(tmp_path: Path) -> None:
    """A bash origin given a kitten-decoded Ctrl-A payload opens a new tab; no sentinel."""
    sentinel = tmp_path / "PWNED"
    # Literal backslash-x01 and backslash-x05 are decoded by kitten into a line-editor Ctrl-A and
    # Ctrl-E, which reorder the typed line so the payload runs. The directory exists so the argv
    # fallback lands somewhere real.
    cwd = f"{tmp_path}/a\\x01touch {sentinel}; \\x05"
    Path(cwd).mkdir(parents=True)
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        origin = _origin_id(socket)
        rc = launcher.launch_scene(
            None,
            None,
            None,
            [launcher.Pane(cwd=cwd), launcher.Pane(title="p1")],
            to=f"unix:{socket}",
            origin_window=origin,
        )
        assert rc == 0
        _poll_absent(sentinel)
        assert not sentinel.exists(), f"injected command ran (bash-escape): {sentinel}"
        _assert_falls_back(socket, origin)


def _other_tab_cwds(socket: Path, origin: int) -> tuple[int, set[str | None]]:
    """Return (tab count, cwds of the windows in the tab that does not hold ``origin``)."""
    tabs = _tabs(socket)
    others = [t for t in tabs if not any(w["id"] == origin for w in t["windows"])]
    return len(tabs), {w.get("cwd") for t in others for w in t["windows"]}


@pytest.mark.parametrize("kind", ["tilde", "var", "relative"])
def test_fill_tab_cross_pane_cwd_agrees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Pane 0 and pane 1 land in the same directory: kitty's, under divergent launcher context."""
    value, kitty_dir = {
        "tilde": ("~/d", tmp_path / "home" / "d"),
        "var": ("$KS_PANE0_DIR/d", tmp_path / "kitty-var" / "d"),
        "relative": ("rel-d", tmp_path / "rel-d"),
    }[kind]
    # kitty's own environment and working directory: spawn_kitty copies os.environ at spawn.
    kitty_dir.mkdir(parents=True)
    (tmp_path / "kitty-var").mkdir(exist_ok=True)
    monkeypatch.setenv("KS_PANE0_DIR", str(tmp_path / "kitty-var"))
    monkeypatch.chdir(tmp_path)
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        # The launcher's own HOME, variable directory and cwd differ from kitty's, each with a `d`,
        # so a launcher-side expansion would land somewhere real and differ from kitty's result.
        client_home = tmp_path / "client-home"
        client_var = tmp_path / "client-var"
        client_cwd = tmp_path / "client-cwd"
        for directory in (client_home / "d", client_var / "d", client_cwd / "rel-d"):
            directory.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(client_home))
        monkeypatch.setenv("KS_PANE0_DIR", str(client_var))
        monkeypatch.chdir(client_cwd)

        origin = _origin_id(socket)
        rc = launcher.launch_scene(
            None,
            None,
            None,
            [launcher.Pane(cwd=value), launcher.Pane(cwd=value)],
            to=f"unix:{socket}",
            origin_window=origin,
        )
        assert rc == 0
        expected = str(kitty_dir.resolve())
        deadline = time.monotonic() + 5.0
        count, cwds = _other_tab_cwds(socket, origin)
        while time.monotonic() < deadline and (count < 2 or cwds != {expected}):
            time.sleep(0.1)
            count, cwds = _other_tab_cwds(socket, origin)
        assert count == 2, f"expected two tabs, got {count}"
        assert cwds == {expected}, f"pane cwds {cwds}, expected kitty-side {expected}"


def test_fill_tab_zsh_equals_word_is_literal(tmp_path: Path) -> None:
    """A zsh origin with magicequalsubst enters `a==bash` in place, not `a=/usr/bin/bash`."""
    zsh = shutil.which("zsh")
    if zsh is None:
        pytest.skip("zsh is not installed")
    target = tmp_path / "a==bash"
    target.mkdir()
    conf = draft_conf(tmp_path, extra_lines=(f"shell {zsh} -f -o magicequalsubst",))
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        origin = _origin_id(socket)
        rc = launcher.launch_scene(
            None,
            None,
            None,
            [launcher.Pane(cwd=str(target)), launcher.Pane(title="p1")],
            to=f"unix:{socket}",
            origin_window=origin,
        )
        assert rc == 0
        cwd: str | None = None
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            _, cwd = _solo_window_and_cwd(socket, origin)
            if cwd == str(target.resolve()):
                break
            time.sleep(0.1)
        assert cwd == str(
            target.resolve()
        ), f"origin cwd {cwd!r}, expected {str(target.resolve())!r}"
        tabs = _tabs(socket)
        assert len(tabs) == 1 and len(tabs[0]["windows"]) == 2, "the scene fills the solo tab"


def test_guard_fill_tab_fish_typeable(tmp_path: Path) -> None:
    """A typeable cwd still fills a fish tab in place: one tab, two windows, origin in the dir."""
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("fish is not installed")
    target = tmp_path / "my dir"
    target.mkdir()
    conf = draft_conf(tmp_path, extra_lines=(f"shell {fish} --no-config --private",))
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        origin = _origin_id(socket)
        rc = launcher.launch_scene(
            None,
            None,
            None,
            [launcher.Pane(cwd=str(target)), launcher.Pane(title="p1")],
            to=f"unix:{socket}",
            origin_window=origin,
        )
        assert rc == 0
        cwd: str | None = None
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            _, cwd = _solo_window_and_cwd(socket, origin)
            if cwd == str(target.resolve()):
                break
            time.sleep(0.1)
        assert cwd == str(
            target.resolve()
        ), f"origin cwd {cwd!r}, expected {str(target.resolve())!r}"
        tabs = _tabs(socket)
        assert len(tabs) == 1 and len(tabs[0]["windows"]) == 2, "a typeable cwd fills in place"
