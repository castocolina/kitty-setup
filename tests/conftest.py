"""Shared pytest fixtures + the integration-test gating mechanism.

Integration tests live under ``tests/integration/`` and are skipped unless
the environment variable ``KITTI_INTEGRATION`` is set to ``1``. This keeps
the default `pytest` run fast and host-independent; the autonomous Kitty
sessions spawn real windows (minimized) and need a working `~/.local/kitty.app`.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

INTEGRATION_ENV_VAR = "KITTI_INTEGRATION"
REPO_ROOT = Path(__file__).resolve().parents[1]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip ``tests/integration/`` items unless ``KITTI_INTEGRATION=1`` is set."""
    del config
    if os.environ.get(INTEGRATION_ENV_VAR) == "1":
        return
    skip = pytest.mark.skip(reason=f"set {INTEGRATION_ENV_VAR}=1 to run integration tests")
    integration_dir = REPO_ROOT / "tests" / "integration"
    for item in items:
        if str(item.path).startswith(str(integration_dir)):
            item.add_marker(skip)


@pytest.fixture()
def windowing_conf() -> str:
    """Return the promoted ``config/kitty/windowing.conf`` text."""
    return (REPO_ROOT / "config" / "kitty" / "windowing.conf").read_text()


@pytest.fixture()
def clear_conf() -> str:
    """Return the promoted ``config/kitty/clear.conf`` text (instant-clear binding)."""
    return (REPO_ROOT / "config" / "kitty" / "clear.conf").read_text()


@pytest.fixture()
def tab_nav_conf() -> str:
    """Return the promoted ``config/kitty/tab-nav.conf`` text (tab-navigation chords)."""
    return (REPO_ROOT / "config" / "kitty" / "tab-nav.conf").read_text()


@pytest.fixture()
def window_nav_conf() -> str:
    """Return the promoted ``config/kitty/window-nav.conf`` text (vim-style window-navigation chords)."""
    return (REPO_ROOT / "config" / "kitty" / "window-nav.conf").read_text()


@pytest.fixture()
def scratch_dir(tmp_path: Path) -> Iterator[Path]:
    """Yield a freshly created scratch directory inside pytest's tmp_path."""
    target = (tmp_path / "scratch").resolve()
    target.mkdir(parents=True, exist_ok=True)
    yield target
