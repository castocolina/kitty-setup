"""h22 — integration tests for `my-kitty window title` / `my-kitty tab title`.

Mirrors `tests/integration/test_h21_remote_control_foundation.py`'s raw-subprocess
pattern (NOT `KittySession`, whose `--listen-on` CLI flag overrides config-level
`listen_on` and so cannot exercise the surface this change ships).

Each test spawns a `kitty --start-as=minimized` against the project's managed
`config/kitty/remote-control.conf`, then drives the promoted `scenes.title`
functions against the live socket. Auto-discovery via pgrep is stubbed to the
spawned PID so the user's daily kitty (if running) does not interfere.

Gated by `KITTI_INTEGRATION=1` per `tests/conftest.py`.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from kitty_setup.scenes import _client, title
from tests.integration._kitty_subprocess import (
    draft_conf,
    kitten_call,
    ls,
    pin_pgrep_to_pid,
    spawn_kitty,
    stub_config,
    wait_for_socket,
)

WINDOW_EMOJI = "🐳 docker test"
TAB_EMOJI = "🐋 monitoring"


def _titles(socket: Path) -> tuple[str, str]:
    """Return (tab_title, window_title) for the only window of the spawned kitty."""
    payload = ls(socket)
    os_window = payload[0]
    tab = os_window["tabs"][0]
    win = tab["windows"][0]
    return tab["title"], win["title"]


def _shell_printf_osc2(socket: Path, label: str) -> None:
    """Drive an OSC-2 escape from the shell side via kitten @ send-text + Enter."""
    cmd = f"printf '\\e]2;{label}\\a'\n"
    result = kitten_call(socket, "send-text", cmd)
    assert result.returncode == 0, f"send-text failed: {result.stderr}"
    time.sleep(0.3)  # let bash run printf and let kitty parse the escape


def test_set_window_title_emoji_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.5)
        pin_pgrep_to_pid(monkeypatch, pid)
        assert title.set_window_title(WINDOW_EMOJI, temporary=True) == 0
        time.sleep(0.2)
        _, win = _titles(socket)
        assert win == WINDOW_EMOJI


def test_set_tab_title_emoji_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.5)
        pin_pgrep_to_pid(monkeypatch, pid)
        assert title.set_tab_title(TAB_EMOJI) == 0
        time.sleep(0.2)
        tab, _ = _titles(socket)
        assert tab == TAB_EMOJI


def test_window_title_temporary_default_allows_osc2_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.8)  # let bash shell-integration settle its own OSC-2
        pin_pgrep_to_pid(monkeypatch, pid)
        assert title.set_window_title("before-osc2", temporary=True) == 0
        time.sleep(0.2)
        _shell_printf_osc2(socket, "after-osc2")
        _, win = _titles(socket)
        # With --temporary, the OSC-2 (or any subsequent shell-integration redraw)
        # must change the title away from what we set.
        assert win != "before-osc2"


def test_window_title_no_temporary_blocks_osc2_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.8)
        pin_pgrep_to_pid(monkeypatch, pid)
        assert title.set_window_title("permanent-window", temporary=False) == 0
        time.sleep(0.2)
        _shell_printf_osc2(socket, "ignored-by-permanent")
        _, win = _titles(socket)
        assert win == "permanent-window"


def test_tab_title_persists_across_osc2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.8)
        pin_pgrep_to_pid(monkeypatch, pid)
        assert title.set_tab_title("labeled-tab") == 0
        time.sleep(0.2)
        _shell_printf_osc2(socket, "tab-should-not-care")
        tab, _ = _titles(socket)
        assert tab == "labeled-tab"


def test_discovery_errors_when_no_kitty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no kitty running and --to unset and $KITTY_LISTEN_ON unset, fail loudly."""
    stub_config(monkeypatch, tmp_path)
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    monkeypatch.setattr(_client, "_pgrep_kitty_pids", lambda: [])
    with pytest.raises(_client.SceneClientError, match="no kitty process found"):
        title.set_window_title("anything", temporary=False)


def test_to_unreachable_socket_propagates_kitten_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--to unix:/nonexistent` propagates kitten's non-zero exit code."""
    stub_config(monkeypatch, tmp_path)
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    bogus = f"unix:{tmp_path}/no-such-socket"
    code = title.set_window_title("anything", temporary=False, to=bogus)
    assert code != 0
