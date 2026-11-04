"""Regression case for T-2-79: an integration case's kitty runs in a scratch HOME (02-12 Task 1).

The case refuses to spawn kitty unless HOME, the four XDG base dirs and HISTFILE resolve under
pytest's basetemp and ZDOTDIR is unset. Refusing first means a tree without the autouse sandbox
fixture fails before anything starts. With the sandbox in place, one real kitty types a nonce, which
must land in the sandbox HISTFILE. Before the sandbox, the developer's real shell history held 143
lines typed by integration cases (tmp/h47-integration-home/real-home.out). This case never reads a
file under the real HOME.
"""

from __future__ import annotations

import os
import shutil
import time
import uuid
from pathlib import Path

import pytest

from tests.integration import _kitty_subprocess

_SANDBOX_NAMES: tuple[str, ...] = (
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
    "XDG_STATE_HOME",
    "HISTFILE",
)


def _resolves_under(value: str | None, base: Path) -> bool:
    return value is not None and Path(value).resolve().is_relative_to(base)


def test_integration_case_runs_in_a_sandboxed_home(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    base = tmp_path_factory.getbasetemp().resolve()
    outside = [name for name in _SANDBOX_NAMES if not _resolves_under(os.environ.get(name), base)]
    if os.environ.get("ZDOTDIR") is not None:
        outside.append("ZDOTDIR")
    if outside:
        pytest.fail(f"refusing to spawn kitty: not sandboxed: {outside}")

    home = Path(os.environ["HOME"]).resolve()
    kitty = _kitty_subprocess.KITTY
    assert kitty.is_file(), kitty
    assert not kitty.resolve().is_relative_to(home), kitty
    kitten = shutil.which("kitten")
    assert kitten is not None, "kitten is not on PATH"
    assert not Path(kitten).resolve().is_relative_to(home), kitten

    histfile = Path(os.environ["HISTFILE"])
    nonce = f"t279-{uuid.uuid4().hex}"
    with _kitty_subprocess.spawn_kitty(_kitty_subprocess.draft_conf(tmp_path), tmp_path) as pid:
        result = _kitty_subprocess.kitten_call(
            _kitty_subprocess.wait_for_socket(pid), "send-text", f"echo {nonce}\n"
        )
        assert result.returncode == 0, result.stderr
        time.sleep(0.5)
    found = False
    deadline = time.monotonic() + 5.0
    while not found and time.monotonic() < deadline:
        found = histfile.is_file() and nonce in histfile.read_text(
            encoding="utf-8", errors="replace"
        )
        time.sleep(0.1)
    assert found, f"the typed nonce did not reach the sandbox HISTFILE {histfile}"
