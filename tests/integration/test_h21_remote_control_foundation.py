"""H21 — remote-control foundation integration test.

Drives a raw ``~/.local/kitty.app/bin/kitty`` process (NOT via
``KittySession`` — the harness passes ``--listen-on=<sock>`` on the CLI,
and that flag overrides config-level ``listen_on``, so the harness cannot
exercise the surface this change ships) configured with the promoted
``config/kitty/remote-control.conf``, polls for the auto-suffixed
``/tmp/kitty-<PID>`` socket to appear, then from a process with
``KITTY_LISTEN_ON`` unset calls ``kitten @ --to unix:/tmp/kitty-<PID> ls``
and asserts the response is non-empty JSON.

Two tests:

* :func:`test_single_instance_socket_reachable` — the spec's load-bearing
  scenario (out-of-process call reaches the socket).
* :func:`test_two_instances_no_collision` — D1 risk row "two concurrent
  instances each have their own socket".

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
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

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_CONTROL_CONF: Final[Path] = REPO_ROOT / "config" / "kitty" / "remote-control.conf"
KITTY: Final[Path] = Path.home() / ".local" / "kitty.app" / "bin" / "kitty"
KITTEN: Final[Path] = Path.home() / ".local" / "kitty.app" / "bin" / "kitten"
SOCKET_BUDGET_S: Final[float] = 5.0


def _draft_conf(scratch: Path) -> Path:
    """Materialise the promoted ``remote-control.conf`` plus a deterministic shell line."""
    conf = scratch / "kitty.conf"
    conf.write_text(
        REMOTE_CONTROL_CONF.read_text(encoding="utf-8") + "\nshell bash --noprofile --norc\n",
        encoding="utf-8",
    )
    return conf


@contextlib.contextmanager
def _spawn_kitty(conf_path: Path, scratch: Path) -> Iterator[int]:
    """Spawn a raw kitty pointing at ``conf_path``; yield its PID; tear down on exit."""
    env = dict(os.environ)
    env.pop("KITTY_LISTEN_ON", None)
    proc = subprocess.Popen(  # noqa: S603 — trusted paths
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
        stale = Path(f"/tmp/kitty-{proc.pid}")  # noqa: S108 — kitty's documented path
        with contextlib.suppress(OSError):
            stale.unlink(missing_ok=True)


def _wait_for_socket(pid: int) -> Path:
    """Poll for ``/tmp/kitty-<pid>`` up to ``SOCKET_BUDGET_S`` seconds."""
    socket = Path(f"/tmp/kitty-{pid}")  # noqa: S108
    deadline = time.monotonic() + SOCKET_BUDGET_S
    while time.monotonic() < deadline:
        if socket.exists():
            return socket
        time.sleep(0.05)
    raise AssertionError(f"socket {socket} did not appear within {SOCKET_BUDGET_S}s")


def _kitten_ls(socket: Path) -> list[dict[str, object]]:
    """Out-of-process ``kitten @ --to unix:<socket> ls``; ``KITTY_LISTEN_ON`` unset."""
    env = dict(os.environ)
    env.pop("KITTY_LISTEN_ON", None)
    result = subprocess.run(  # noqa: S603 — trusted paths
        [str(KITTEN), "@", f"--to=unix:{socket}", "ls"],
        capture_output=True,
        check=False,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0, (
        f"kitten @ ls against {socket} returned {result.returncode}: "
        f"{result.stderr.decode('utf-8', errors='replace')}"
    )
    payload = json.loads(result.stdout.decode("utf-8", errors="replace"))
    assert isinstance(payload, list), f"expected list, got {type(payload).__name__}"
    return payload


def test_single_instance_socket_reachable(tmp_path: Path) -> None:
    """The spec's load-bearing scenario — out-of-process call reaches the socket."""
    conf = _draft_conf(tmp_path)
    with _spawn_kitty(conf, tmp_path) as pid:
        socket = _wait_for_socket(pid)
        payload = _kitten_ls(socket)
    assert len(payload) >= 1, f"expected ≥1 OS-window entry, got {payload!r}"
    first = payload[0]
    assert isinstance(first, dict) and "tabs" in first


def test_two_instances_no_collision(tmp_path: Path) -> None:
    """Two concurrent kitty instances → two distinct sockets, each reachable only via its own PID."""
    conf = _draft_conf(tmp_path)
    with _spawn_kitty(conf, tmp_path) as pid1, _spawn_kitty(conf, tmp_path) as pid2:
        assert pid1 != pid2
        sock1 = _wait_for_socket(pid1)
        sock2 = _wait_for_socket(pid2)
        assert sock1 != sock2, f"expected distinct sockets, got {sock1} == {sock2}"
        payload1 = _kitten_ls(sock1)
        payload2 = _kitten_ls(sock2)
    assert len(payload1) >= 1
    assert len(payload2) >= 1
