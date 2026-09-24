"""Unit tests for the ``XDG_RUNTIME_DIR`` fallback ``KittySession`` hands its child (02-10).

``_spawn_kitty`` builds the child env from ``os.environ`` and applies
``env.setdefault("XDG_RUNTIME_DIR", <fallback>)``. The fallback must be
``tempfile.gettempdir()`` — the stdlib answer to "where is the temp directory" — not a
literal. No kitty is started: ``subprocess.Popen`` is a recorder, ``_wait_for_socket`` a
no-op, and the binaries fake paths, the same shape ``tests/unit/test_kitty_session_socket.py``
uses. Private names are patched by string so the tests stay pyright-strict clean.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from kitty_setup.harness import kitty_session
from kitty_setup.harness.kitty_session import KittyBinaries, KittySession

_FAKE_BINARIES = KittyBinaries(kitty=Path("/nonexistent/kitty"), kitten=Path("/nonexistent/kitten"))


def _no_op(self: KittySession) -> None:
    del self


class _RecorderPopen:
    """Records the ``env`` it is handed; never spawns anything."""

    instances: list[dict[str, str]]

    def __init__(self, argv: list[str], **kwargs: Any) -> None:
        del argv
        env: dict[str, str] = kwargs.get("env") or {}
        _RecorderPopen.instances.append(env)
        self.pid = 0

    def poll(self) -> int:
        return 0


@pytest.fixture()
def recorder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[dict[str, str]]:
    """Replace ``subprocess.Popen`` with the recorder and ``_wait_for_socket`` with a no-op."""
    _RecorderPopen.instances = []
    monkeypatch.setattr(kitty_session.subprocess, "Popen", _RecorderPopen)
    monkeypatch.setattr(KittySession, "_wait_for_socket", _no_op)
    monkeypatch.delenv("KEEP_SESSIONS", raising=False)
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    # The sessions root under tmp_path is too deep for sun_path; a short dir is required.
    short = tmp_path / "short"
    short.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(short))
    monkeypatch.setattr(kitty_session, "_sessions_root", lambda: short / "sessions")
    (short / "sessions").mkdir()
    return _RecorderPopen.instances


def test_runtime_dir_fallback_is_gettempdir(recorder: list[dict[str, str]], tmp_path: Path) -> None:
    """With XDG_RUNTIME_DIR unset, the child env carries tempfile.gettempdir()."""
    with KittySession(cwd=tmp_path, binaries=_FAKE_BINARIES) as session:
        del session
    assert len(recorder) == 1, "exactly one child env must be observed"
    assert recorder[0]["XDG_RUNTIME_DIR"] == tempfile.gettempdir()


def test_guard_runtime_dir_kept_when_set(
    recorder: list[dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A set XDG_RUNTIME_DIR reaches the child unchanged."""
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    with KittySession(cwd=Path("/tmp"), binaries=_FAKE_BINARIES) as session:
        del session
    assert len(recorder) == 1, "exactly one child env must be observed"
    assert recorder[0]["XDG_RUNTIME_DIR"] == "/run/user/1000"
