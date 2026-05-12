"""H01 — new tabs / OS windows / splits inherit the launching window's cwd.

Promoted from ``tmp/h01-cwd-inheritance/run.py``. See ``docs/repro/h01-cwd.md``
for the manual repro and the rationale for testing the action rather than the
keystroke.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from kitty_setup.harness.kitty_session import KittySession


def _foreground_cwd(window: dict[str, Any]) -> str:
    fg = window.get("foreground_processes", [])
    if fg and "cwd" in fg[0]:
        return str(fg[0]["cwd"])
    return str(window.get("cwd", ""))


def _new_window(snapshot: list[dict[str, Any]], baseline_ids: set[int]) -> dict[str, Any]:
    for os_win in snapshot:
        for tab in os_win.get("tabs", []):
            for win in tab.get("windows", []):
                if win["id"] not in baseline_ids:
                    return win
    raise AssertionError("no new window found in post-launch snapshot")


@pytest.mark.parametrize(
    ("label", "kwargs"),
    [
        ("new-tab", {"type": "tab", "cwd": "current"}),
        ("new-os-window", {"type": "os-window", "cwd": "current"}),
        # phase1-curated-bindings-revert-defaults dropped the vsplit/hsplit
        # chord pair (D2); the cwd-inheriting "new window in current tab"
        # behaviour is now delivered exclusively via ctrl+shift+enter, which
        # launches with no --location pin. Placement follows kitty's active
        # layout (the user cycles layouts with ctrl+shift+l).
        ("new-window", {"cwd": "current"}),
    ],
)
def test_launch_inherits_cwd(
    label: str,
    kwargs: dict[str, str],
    scratch_dir: Path,
    windowing_conf: str,
) -> None:
    del label  # used only for parametrize id
    with KittySession(cwd=scratch_dir, config_snippets=[windowing_conf]) as session:
        before = session.ls()
        baseline_ids: set[int] = {
            w["id"]
            for os_win in before
            for tab in os_win.get("tabs", [])
            for w in tab.get("windows", [])
        }
        session.launch(**kwargs)
        after = session.ls()
        new_win = _new_window(after, baseline_ids)
        observed = _foreground_cwd(new_win)
        assert observed == str(scratch_dir), f"expected cwd={scratch_dir}, observed cwd={observed}"
