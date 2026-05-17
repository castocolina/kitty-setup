"""Shared subprocess helpers for raw-kitty integration tests.

Extracted from `test_h22_window_title.py` (originally inline as `_draft_conf` /
`_spawn_kitty` / `_wait_for_socket` / `_stub_config` / `_pin_pgrep_to_pid`)
so the h23 styling tests can reuse the same code path. Pytest does not
collect this module because the leading underscore in the filename
suppresses collection.

These helpers spawn `kitty --start-as=minimized` against the repo's managed
`remote-control.conf`, then expose the listen socket so callers can drive
`kitten @ …` directly. Auto-discovery via pgrep is pinned to the spawned PID
so the user's daily kitty (if running) does not interfere.
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
from kitty_setup.scenes import _client

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
REMOTE_CONTROL_CONF: Final[Path] = REPO_ROOT / "config" / "kitty" / "remote-control.conf"
KITTY: Final[Path] = Path.home() / ".local" / "kitty.app" / "bin" / "kitty"
KITTEN: Final[Path] = Path.home() / ".local" / "kitty.app" / "bin" / "kitten"
SOCKET_BUDGET_S: Final[float] = 5.0


def draft_conf(
    scratch: Path,
    *,
    extra_lines: tuple[str, ...] = (),
    name: str = "kitty.conf",
) -> Path:
    """Materialise a kitty conf that includes `remote-control.conf` + `shell bash`."""
    conf = scratch / name
    base = [
        REMOTE_CONTROL_CONF.read_text(encoding="utf-8").rstrip("\n"),
        "shell bash --noprofile --norc",
    ]
    conf.write_text("\n".join((*base, *extra_lines)) + "\n", encoding="utf-8")
    return conf


@contextlib.contextmanager
def spawn_kitty(conf_path: Path, scratch: Path) -> Iterator[int]:
    """Spawn `kitty --start-as=minimized` against `conf_path`; yield the PID."""
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


def wait_for_socket(pid: int) -> Path:
    """Block until `/tmp/kitty-<pid>` exists or SOCKET_BUDGET_S elapses."""
    socket = Path(f"/tmp/kitty-{pid}")  # noqa: S108
    deadline = time.monotonic() + SOCKET_BUDGET_S
    while time.monotonic() < deadline:
        if socket.exists():
            return socket
        time.sleep(0.05)
    raise AssertionError(f"socket {socket} did not appear within {SOCKET_BUDGET_S}s")


def stub_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point `ConfigPaths.for_user` at a tmp_path-rooted payload with managed conf."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    paths = config_updater.ConfigPaths.for_user(home=home)
    paths.payload_dir.mkdir(parents=True, exist_ok=True)
    (paths.payload_dir / "remote-control.conf").write_text(
        REMOTE_CONTROL_CONF.read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(
        config_updater.ConfigPaths,
        "for_user",
        classmethod(lambda cls, home=None: paths),
    )


def pin_pgrep_to_pid(monkeypatch: pytest.MonkeyPatch, pid: int) -> None:
    """Pin `_pgrep_kitty_pids()` to the spawned PID for deterministic discovery."""
    monkeypatch.setattr(_client, "_pgrep_kitty_pids", lambda: [pid])
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)


def kitten_call(socket: Path, *args: str, timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    """Run `kitten @ --to=unix:<socket> <args…>` and return the CompletedProcess."""
    env = dict(os.environ)
    env.pop("KITTY_LISTEN_ON", None)
    return subprocess.run(
        [str(KITTEN), "@", f"--to=unix:{socket}", *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        env=env,
    )


def ls(socket: Path) -> list[dict]:
    """Return parsed `kitten @ ls` JSON; raise AssertionError on non-zero exit."""
    result = kitten_call(socket, "ls")
    assert result.returncode == 0, f"kitten @ ls failed: {result.stderr}"
    return json.loads(result.stdout)


def get_color(socket: Path, key: str, match: str | None = None) -> str | None:
    """Return the value of a color key from `kitten @ get-colors`, or None on failure."""
    args = ["get-colors"]
    if match is not None:
        args.extend(["--match", match])
    result = kitten_call(socket, *args)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith(f"{key} "):
            return line.split(None, 1)[1].strip()
    return None
