"""Autouse HOME sandbox for every integration case (02-12, T-2-79).

Each case gets HOME, the four XDG base directories and HISTFILE under pytest's basetemp, ZDOTDIR
dropped, and the real kitty bin directory first on PATH. Before this fixture, the developer's real
``~/.bash_history`` held 143 lines typed by integration cases
(``tmp/h47-integration-home/real-home.out``): kitty's bash saved its history into the real HOME.
``XDG_RUNTIME_DIR`` is kept for the compositor's socket and the tools.

HOME is set at test time rather than in the runner's environment. The kitty and kitten constants
bind at import, so a runner-level HOME would make every case look for kitty in an empty sandbox.
The bin directory is read at this module's import, while HOME is still the real one.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import pytest

from kitty_setup import installer

# Read at import, while HOME is still the real one: a child `my-kitty` re-imports `installer` under
# the sandbox HOME and must still find the real `kitten` on PATH.
_KITTY_BIN: Final[Path] = installer.DEFAULT_DEST / "kitty.app" / "bin"


@pytest.fixture(autouse=True)
def sandbox_integration_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    home = tmp_path_factory.mktemp("home")
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
    monkeypatch.delenv("ZDOTDIR", raising=False)
    monkeypatch.setenv("PATH", f"{_KITTY_BIN}{os.pathsep}{os.environ.get('PATH', '')}")
