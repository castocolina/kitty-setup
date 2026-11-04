"""Unit tests for where ``KittySession`` puts its control socket (R0.13, plan 02-11).

A Unix-domain socket address is a ``sockaddr_un``, whose ``sun_path`` field is **108 bytes**
on Linux, including the terminating NUL — so a socket path may be at most **107 bytes**. kitty
given a longer ``--listen-on=unix:<path>`` logs ``Invalid listen_on=…, ignoring`` and never
opens the socket. Measured in 02-11: from a harness worktree under ``.claude/worktrees/`` the
old ``<repo>/tmp/sessions/s<10 hex>/sock`` path was 114 bytes, and every KittySession test
failed with ``HarnessStartupError``. The socket path must therefore not depend on how deep
the checkout is.

No kitty is started: ``_spawn_kitty`` and ``_wait_for_socket`` are replaced, and the binaries
are fake paths. Private names are patched by string so the tests stay pyright-strict clean.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from kitty_setup.harness import kitty_session
from kitty_setup.harness.kitty_session import HarnessStartupError, KittyBinaries, KittySession

# sockaddr_un.sun_path is 108 bytes on Linux; one is the terminating NUL.
SUN_PATH_BYTES = 108
SOCKET_PATH_BUDGET = SUN_PATH_BYTES - 1

_FAKE_BINARIES = KittyBinaries(kitty=Path("/nonexistent/kitty"), kitten=Path("/nonexistent/kitten"))


def _no_op(self: KittySession) -> None:
    del self


@pytest.fixture()
def deep_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``_sessions_root()`` at a directory far deeper than any real checkout."""
    root = tmp_path / ("d" * 60) / ("e" * 60) / "tmp" / "sessions"
    root.mkdir(parents=True)
    monkeypatch.setattr(kitty_session, "_sessions_root", lambda: root)
    monkeypatch.setattr(KittySession, "_spawn_kitty", _no_op)
    monkeypatch.setattr(KittySession, "_wait_for_socket", _no_op)
    monkeypatch.delenv("KEEP_SESSIONS", raising=False)
    return root


def _socket_len(path: Path) -> int:
    return len(bytes(path))


def test_socket_path_fits_sun_path_from_a_deep_checkout(
    deep_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the sessions root >108 bytes deep, the socket path is still <= 107 bytes."""
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    assert _socket_len(deep_root) > SUN_PATH_BYTES, "the fixture must really be deep"
    with KittySession(cwd=deep_root, binaries=_FAKE_BINARIES) as session:
        assert _socket_len(session.socket_path) <= SOCKET_PATH_BUDGET, session.socket_path
        assert session.session_dir.parent == deep_root, "evidence stays under the repo's tmp/"


def test_socket_dir_is_private_and_under_the_runtime_dir(
    deep_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path / "run"
    runtime.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    with KittySession(cwd=deep_root, binaries=_FAKE_BINARIES) as session:
        socket_dir = session.socket_path.parent
        assert socket_dir.parent == runtime
        assert stat.S_IMODE(socket_dir.stat().st_mode) == 0o700
        assert _socket_len(session.socket_path) <= SOCKET_PATH_BUDGET


@pytest.mark.parametrize("keep", ["0", "1"])
def test_socket_dir_is_removed_on_teardown_even_when_sessions_are_kept(
    deep_root: Path, monkeypatch: pytest.MonkeyPatch, keep: str
) -> None:
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.setenv("KEEP_SESSIONS", keep)
    with KittySession(cwd=deep_root, binaries=_FAKE_BINARIES) as session:
        socket_dir = session.socket_path.parent
        session_dir = session.session_dir
        assert socket_dir.is_dir()
        assert socket_dir != session_dir
    assert not socket_dir.exists(), "a stale socket directory was left behind"
    assert session_dir.exists() == (keep == "1"), "KEEP_SESSIONS still governs the evidence"


def test_socket_dir_is_removed_when_startup_fails(
    deep_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    seen: list[Path] = []

    def never_ready(self: KittySession) -> None:
        seen.append(self.socket_path)
        raise HarnessStartupError("simulated: socket never ready")

    monkeypatch.setattr(KittySession, "_wait_for_socket", never_ready)
    with (
        pytest.raises(HarnessStartupError),
        KittySession(cwd=deep_root, binaries=_FAKE_BINARIES),
    ):
        pass
    assert len(seen) == 1
    assert _socket_len(seen[0]) <= SOCKET_PATH_BUDGET, seen[0]
    assert not seen[0].parent.exists(), "a stale socket directory was left behind"
