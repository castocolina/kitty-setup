"""h24 — integration tests for the mirrored Tall layout chord (Phase 2 §11).

Promotes the green probe at `tmp/h24-tall-mirrored-right/run.py` to the CI
surface. Spawns `kitty --start-as=minimized` against a draft config that
includes the SHIPPED `config/kitty/layout.conf` — so the curated
`enabled_layouts tall,tall:mirrored=true,fat,grid,horizontal,vertical,splits,stack`
directive is loaded exactly as a user would experience it after `make install`.

Phase A of the probe (vanilla `enabled_layouts *`; option silently ignored)
is NOT promoted: that configuration is what the change deliberately does
NOT ship, and codifying it as a test would create maintenance surface for
rejected behaviour. The Phase A finding lives in the repro doc's
Attempted-Alternatives section and in the locked `expected.json`.

Gated by `KITTI_INTEGRATION=1` per `tests/conftest.py`.
"""

from __future__ import annotations

import time
from pathlib import Path

from tests.integration._kitty_subprocess import (
    REPO_ROOT,
    draft_conf,
    kitten_call,
    ls,
    spawn_kitty,
    wait_for_socket,
)

LAYOUT_CONF: Path = REPO_ROOT / "config" / "kitty" / "layout.conf"


def _layout_signature(ls_payload: list[dict]) -> str:
    """Return a stable "name + options" string for the active layout.

    `tab["layout"]` is just the base name (e.g. "tall") — identical for
    mirrored and non-mirrored. `tab["layout_opts"]` carries the options
    dict that distinguishes them. Probe-grounded; ported from
    `tmp/h24-tall-mirrored-right/run.py`.
    """
    tab = ls_payload[0]["tabs"][0]
    name = tab["layout"]
    opts = tab.get("layout_opts") or {}
    if not opts:
        return name
    parts = ";".join(f"{k}={v}" for k, v in sorted(opts.items()))
    return f"{name}:{parts}"


def _pane_summary(ls_payload: list[dict]) -> dict:
    """Return a neighbors-aware summary of the panes.

    `kitten @ ls` does NOT expose pixel geometry in kitty 0.46.2, so
    `window["neighbors"]` is the only reliable signal for left/right
    structure. The "main" pane in tall is the one with maximum lines
    (full height); in mirrored=true it should have neighbors.left populated.
    """
    tab = ls_payload[0]["tabs"][0]
    windows = tab["windows"]
    summary: dict = {
        "window_count": len(windows),
        "main_pane_id": None,
        "main_pane_has_left_neighbors": None,
        "main_pane_has_right_neighbors": None,
    }
    max_lines = -1
    main: dict | None = None
    for win in windows:
        lines = win.get("lines") or 0
        if lines > max_lines:
            max_lines = lines
            main = win
    if main is not None:
        nb = main.get("neighbors") or {}
        summary["main_pane_id"] = main.get("id")
        summary["main_pane_has_left_neighbors"] = bool(nb.get("left"))
        summary["main_pane_has_right_neighbors"] = bool(nb.get("right"))
    return summary


def _ensure_3_panes(socket: Path) -> int:
    current = len(ls(socket)[0]["tabs"][0]["windows"])
    while current < 3:
        result = kitten_call(socket, "launch", "--type=window", "--no-response")
        assert result.returncode == 0, f"launch failed: {result.stderr}"
        time.sleep(0.3)
        current = len(ls(socket)[0]["tabs"][0]["windows"])
    return current


def _draft_with_layout(scratch: Path) -> Path:
    layout_text = LAYOUT_CONF.read_text(encoding="utf-8").rstrip("\n")
    return draft_conf(scratch, extra_lines=(layout_text,), name="kitty-h24.conf")


def test_curated_enabled_layouts_initial_state_is_plain_tall(tmp_path: Path) -> None:
    conf = _draft_with_layout(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.5)
        # With `enabled_layouts tall,tall:mirrored=true,…`, kitty picks the FIRST
        # entry as the default — plain `tall` (mirrored=n).
        result = kitten_call(socket, "goto-layout", "tall")
        assert result.returncode == 0, f"goto-layout tall failed: {result.stderr}"
        time.sleep(0.3)
        assert _layout_signature(ls(socket)) == "tall:bias=50;full_size=1;mirrored=n"


def test_goto_layout_tall_mirrored_true_applies_option_with_curated_pin(
    tmp_path: Path,
) -> None:
    conf = _draft_with_layout(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.5)
        result = kitten_call(socket, "goto-layout", "tall:mirrored=true")
        assert result.returncode == 0, (
            f"goto-layout tall:mirrored=true failed: {result.stderr}"
        )
        time.sleep(0.3)
        payload = ls(socket)
        # Load-bearing assertion: the option ACTUALLY APPLIED. Exit 0 alone is
        # not enough (Phase A of the probe shows it can succeed silently with
        # mirrored=n when enabled_layouts is unpinned).
        assert payload[0]["tabs"][0]["layout_opts"]["mirrored"] == "y"


def test_mirrored_tall_puts_main_pane_on_right_with_curated_pin(tmp_path: Path) -> None:
    conf = _draft_with_layout(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.5)
        _ensure_3_panes(socket)
        result = kitten_call(socket, "goto-layout", "tall:mirrored=true")
        assert result.returncode == 0, f"goto-layout failed: {result.stderr}"
        time.sleep(0.3)
        summary = _pane_summary(ls(socket))
        assert summary["window_count"] == 3
        # Main (full-height) pane has the OTHER panes on its LEFT — i.e. it is
        # the rightmost column. Plain tall would have right-side neighbors instead.
        assert summary["main_pane_has_left_neighbors"] is True
        assert summary["main_pane_has_right_neighbors"] is False


def test_curated_enabled_layouts_cycle_includes_mirrored_variant(tmp_path: Path) -> None:
    conf = _draft_with_layout(tmp_path)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.5)
        # Land on plain `tall` so the cycle starts from a known position.
        result = kitten_call(socket, "goto-layout", "tall")
        assert result.returncode == 0
        time.sleep(0.3)
        observed: list[str] = []
        for _ in range(10):
            r = kitten_call(socket, "action", "next_layout")
            assert r.returncode == 0, f"action next_layout failed: {r.stderr}"
            time.sleep(0.2)
            observed.append(_layout_signature(ls(socket)))
        # Within one full pass through the 8-entry curated list, BOTH the
        # plain and mirrored Tall signatures appear as distinct cycle steps.
        assert "tall:bias=50;full_size=1;mirrored=n" in observed
        assert "tall:bias=50;full_size=1;mirrored=y" in observed
