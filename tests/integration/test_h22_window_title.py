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

import contextlib
import json
import os
import signal
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pytest

from kitty_setup import config_updater
from kitty_setup.scenes import _client, title

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_CONTROL_CONF: Final[Path] = REPO_ROOT / "config" / "kitty" / "remote-control.conf"
KITTY: Final[Path] = Path.home() / ".local" / "kitty.app" / "bin" / "kitty"
KITTEN: Final[Path] = Path.home() / ".local" / "kitty.app" / "bin" / "kitten"
SOCKET_BUDGET_S: Final[float] = 5.0

WINDOW_EMOJI = "🐳 docker test"
TAB_EMOJI = "🐋 monitoring"


def _draft_conf(scratch: Path) -> Path:
    conf = scratch / "kitty.conf"
    conf.write_text(
        REMOTE_CONTROL_CONF.read_text(encoding="utf-8") + "\nshell bash --noprofile --norc\n",
        encoding="utf-8",
    )
    return conf


@contextlib.contextmanager
def _spawn_kitty(conf_path: Path, scratch: Path) -> Iterator[int]:
    env = dict(os.environ)
    env.pop("KITTY_LISTEN_ON", None)
    proc = subprocess.Popen(
        [
            str(KITTY),
            f"--config={conf_path}",
            "--start-as=minimized",
            f"--directory={scratch}",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield proc.pid
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
        stale = Path(f"/tmp/kitty-{proc.pid}")  # noqa: S108
        with contextlib.suppress(OSError):
            stale.unlink(missing_ok=True)


def _wait_for_socket(pid: int) -> Path:
    socket = Path(f"/tmp/kitty-{pid}")  # noqa: S108
    deadline = time.monotonic() + SOCKET_BUDGET_S
    while time.monotonic() < deadline:
        if socket.exists():
            return socket
        time.sleep(0.05)
    raise AssertionError(f"socket {socket} did not appear within {SOCKET_BUDGET_S}s")


def _stub_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point ConfigPaths.for_user at a tmp_path-rooted payload with the managed conf."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    paths = config_updater.ConfigPaths.for_user(home=home)
    paths.payload_dir.mkdir(parents=True, exist_ok=True)
    (paths.payload_dir / "remote-control.conf").write_text(
        REMOTE_CONTROL_CONF.read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(
        config_updater.ConfigPaths, "for_user", classmethod(lambda cls, home=None: paths)
    )


def _pin_pgrep_to_pid(monkeypatch: pytest.MonkeyPatch, pid: int) -> None:
    """Make _pgrep_kitty_pids() return exactly the spawned PID so discovery is deterministic."""
    monkeypatch.setattr(_client, "_pgrep_kitty_pids", lambda: [pid])
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)


def _ls(socket: Path) -> list[dict]:
    result = subprocess.run(
        [str(KITTEN), "@", f"--to=unix:{socket}", "ls"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, f"kitten @ ls failed: {result.stderr}"
    return json.loads(result.stdout)


def _titles(socket: Path) -> tuple[str, str]:
    """Return (tab_title, window_title) for the only window of the spawned kitty."""
    payload = _ls(socket)
    os_window = payload[0]
    tab = os_window["tabs"][0]
    win = tab["windows"][0]
    return tab["title"], win["title"]


def _shell_printf_osc2(socket: Path, label: str) -> None:
    """Drive an OSC-2 escape from the shell side via kitten @ send-text + Enter."""
    cmd = f"printf '\\e]2;{label}\\a'\n"
    result = subprocess.run(
        [str(KITTEN), "@", f"--to=unix:{socket}", "send-text", cmd],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, f"send-text failed: {result.stderr}"
    time.sleep(0.3)  # let bash run printf and let kitty parse the escape


def test_set_window_title_emoji_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_config(monkeypatch, tmp_path)
    conf = _draft_conf(tmp_path)
    with _spawn_kitty(conf, tmp_path) as pid:
        socket = _wait_for_socket(pid)
        time.sleep(0.5)
        _pin_pgrep_to_pid(monkeypatch, pid)
        assert title.set_window_title(WINDOW_EMOJI, temporary=True) == 0
        time.sleep(0.2)
        _, win = _titles(socket)
        assert win == WINDOW_EMOJI


def test_set_tab_title_emoji_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_config(monkeypatch, tmp_path)
    conf = _draft_conf(tmp_path)
    with _spawn_kitty(conf, tmp_path) as pid:
        socket = _wait_for_socket(pid)
        time.sleep(0.5)
        _pin_pgrep_to_pid(monkeypatch, pid)
        assert title.set_tab_title(TAB_EMOJI) == 0
        time.sleep(0.2)
        tab, _ = _titles(socket)
        assert tab == TAB_EMOJI


def test_window_title_temporary_default_allows_osc2_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_config(monkeypatch, tmp_path)
    conf = _draft_conf(tmp_path)
    with _spawn_kitty(conf, tmp_path) as pid:
        socket = _wait_for_socket(pid)
        time.sleep(0.8)  # let bash shell-integration settle its own OSC-2
        _pin_pgrep_to_pid(monkeypatch, pid)
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
    _stub_config(monkeypatch, tmp_path)
    conf = _draft_conf(tmp_path)
    with _spawn_kitty(conf, tmp_path) as pid:
        socket = _wait_for_socket(pid)
        time.sleep(0.8)
        _pin_pgrep_to_pid(monkeypatch, pid)
        assert title.set_window_title("permanent-window", temporary=False) == 0
        time.sleep(0.2)
        _shell_printf_osc2(socket, "ignored-by-permanent")
        _, win = _titles(socket)
        assert win == "permanent-window"


def test_tab_title_persists_across_osc2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_config(monkeypatch, tmp_path)
    conf = _draft_conf(tmp_path)
    with _spawn_kitty(conf, tmp_path) as pid:
        socket = _wait_for_socket(pid)
        time.sleep(0.8)
        _pin_pgrep_to_pid(monkeypatch, pid)
        assert title.set_tab_title("labeled-tab") == 0
        time.sleep(0.2)
        _shell_printf_osc2(socket, "tab-should-not-care")
        tab, _ = _titles(socket)
        assert tab == "labeled-tab"


def test_discovery_errors_when_no_kitty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no kitty running and --to unset and $KITTY_LISTEN_ON unset, fail loudly."""
    _stub_config(monkeypatch, tmp_path)
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    monkeypatch.setattr(_client, "_pgrep_kitty_pids", lambda: [])
    with pytest.raises(_client.SceneClientError, match="no kitty process found"):
        title.set_window_title("anything", temporary=False)


def test_to_unreachable_socket_propagates_kitten_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--to unix:/nonexistent` propagates kitten's non-zero exit code."""
    _stub_config(monkeypatch, tmp_path)
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    bogus = f"unix:{tmp_path}/no-such-socket"
    code = title.set_window_title("anything", temporary=False, to=bogus)
    assert code != 0
