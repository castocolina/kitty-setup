"""H21 — end-to-end doctor remote-control reachability check.

Materialises a fake ``ConfigPaths`` rooted at ``tmp_path/home`` carrying a
verbatim copy of ``config/kitty/remote-control.conf``, spawns a raw kitty
process pointing at the same config (so it actually creates the
``/tmp/kitty-<PID>`` socket), and calls the doctor's
``_check_remote_control_per_probe_04`` directly. Asserts the result is PASS
with "reachable on 1 kitty instance".

Cannot use ``KittySession`` here: the harness passes ``--listen-on=<sock>``
on the CLI, which overrides the config's ``listen_on``. h21 needs the
config-level surface, so it spawns raw subprocess (same shape as
``test_h21_remote_control_foundation.py``).

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from kitty_setup import config_updater, doctor

REPO_ROOT = Path(__file__).resolve().parents[2]
REMOTE_CONTROL_CONF: Final[Path] = REPO_ROOT / "config" / "kitty" / "remote-control.conf"
KITTY: Final[Path] = Path.home() / ".local" / "kitty.app" / "bin" / "kitty"
SOCKET_BUDGET_S: Final[float] = 5.0


def _materialise_paths(tmp_path: Path) -> config_updater.ConfigPaths:
    """Build a ``ConfigPaths`` whose ``payload_dir`` carries our ``remote-control.conf``."""
    home = tmp_path / "home"
    home.mkdir()
    paths = config_updater.ConfigPaths.for_user(home=home)
    paths.payload_dir.mkdir(parents=True)
    (paths.payload_dir / "remote-control.conf").write_text(
        REMOTE_CONTROL_CONF.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return paths


@contextlib.contextmanager
def _spawn_kitty(conf_path: Path, scratch: Path) -> Iterator[int]:
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
    socket = Path(f"/tmp/kitty-{pid}")  # noqa: S108
    deadline = time.monotonic() + SOCKET_BUDGET_S
    while time.monotonic() < deadline:
        if socket.exists():
            return socket
        time.sleep(0.05)
    raise AssertionError(f"socket {socket} did not appear within {SOCKET_BUDGET_S}s")


def test_doctor_reports_pass_when_managed_kitty_running(tmp_path: Path) -> None:
    """End-to-end: managed config + running kitty → doctor PASSes with "reachable on 1 ..."."""
    paths = _materialise_paths(tmp_path)
    conf = paths.payload_dir / "remote-control.conf"
    # Append shell deterministic line so spawn doesn't pop a wizard.
    conf.write_text(conf.read_text() + "\nshell bash --noprofile --norc\n", encoding="utf-8")

    with _spawn_kitty(conf, tmp_path) as pid:
        _wait_for_socket(pid)
        result = doctor._check_remote_control_per_probe_04(paths)

    assert result.passed is True, f"expected PASS, got {result.render()}"
    assert result.skipped is False
    assert "reachable on 1 kitty instance" in result.detail
