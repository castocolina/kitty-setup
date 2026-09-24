"""Integration test for `scenes/_client.py:_resolve_socket` against a live kitty.

Short-circuit branches ($KITTY_LISTEN_ON, --to) are unit-only per R7;
this file covers only the pgrep-derived discovery path. It spawns a raw
kitty (NOT KittySession — the harness passes --listen-on on the CLI,
which would defeat the test of config-driven listen_on) and verifies
that `_resolve_socket(None)` resolves to the right `unix:<base>-<PID>`
and that `kitten_at` reaches the live process.

R7 promotion gate for the unit stubs in
`tests/unit/test_scenes_client.py`.

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
from kitty_setup.scenes import _client

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_CONTROL_CONF: Final[Path] = REPO_ROOT / "config" / "kitty" / "remote-control.conf"
KITTY: Final[Path] = Path.home() / ".local" / "kitty.app" / "bin" / "kitty"
SOCKET_BUDGET_S: Final[float] = 5.0


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


def _stub_config_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, listen_on_base: str = "/tmp/kitty"
) -> None:
    """Install a fake ConfigPaths whose remote-control.conf has the given listen_on base."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    paths = config_updater.ConfigPaths.for_user(home=home)
    paths.payload_dir.mkdir(parents=True, exist_ok=True)
    (paths.payload_dir / "remote-control.conf").write_text(
        f"allow_remote_control yes\nlisten_on unix:{listen_on_base}\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        config_updater.ConfigPaths,
        "for_user",
        classmethod(lambda cls, home=None: paths),
    )


def test_resolve_socket_pgrep_path_against_live_kitty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_resolve_socket(None)` returns the right unix:<base>-<PID> for a live kitty."""
    monkeypatch.delenv("KITTY_LISTEN_ON", raising=False)
    _stub_config_paths(monkeypatch, tmp_path)
    conf = _draft_conf(tmp_path)

    with _spawn_kitty(conf, tmp_path) as pid:
        socket_file = _wait_for_socket(pid)
        # Constrain pgrep to the spawned PID so we don't pick up the user's
        # own kitty processes (the user's daily kitty IS running during tests).
        monkeypatch.setattr(_client, "pgrep_kitty_pids", lambda: [pid])

        resolved = _client._resolve_socket(None)
        assert resolved == f"unix:{socket_file}"

        # And kitten_at actually reaches the live process via that socket.
        result = _client.kitten_at("ls")
        assert result.returncode == 0, f"kitten @ ls failed: {result.stderr}"
        payload = json.loads(result.stdout)
        assert isinstance(payload, list) and len(payload) >= 1
