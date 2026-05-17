"""h23 — integration tests for Phase 2 §9 (tab accent) + §10 (window styling).

Promotes `tmp/h23-styling/run.py` to the gated integration suite. Each test
spawns a `kitty --start-as=minimized` against the project's managed
`remote-control.conf` (plus `dynamic_background_opacity yes` for opacity tests,
explicitly omitted for the precondition test), then drives the promoted
`scenes.{accent,background,font,opacity}` functions against the live socket.

Replicates every assertion captured in `tmp/h23-styling/expected.json` — the
mapping is documented in `phase2-scene-styling/design.md` D7 and elaborated in
`phase2-scene-styling/tasks.md` §6.1.1.

Gated by `KITTI_INTEGRATION=1` per `tests/conftest.py`.
"""

from __future__ import annotations

import time

import pytest

from kitty_setup.scenes import accent, background, font, opacity
from tests.integration._kitty_subprocess import (
    draft_conf,
    get_color,
    kitten_call,
    ls,
    pin_pgrep_to_pid,
    spawn_kitty,
    stub_config,
    wait_for_socket,
)

DYNAMIC_OPACITY_LINE = ("dynamic_background_opacity yes",)
OPACITY_PRECONDITION_STDERR = (
    "You must turn on the dynamic_background_opacity option in kitty.conf"
)


def test_opacity_without_directive_errors_clearly(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """§6.2: vanilla conf (no dynamic_background_opacity) — kitten errors clearly."""
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path)  # NO dynamic_background_opacity line
    with spawn_kitty(conf, tmp_path) as pid:
        wait_for_socket(pid)
        time.sleep(0.4)
        pin_pgrep_to_pid(monkeypatch, pid)
        rc = opacity.set_os_window_opacity(0.5)
    assert rc != 0
    err = capsys.readouterr().err
    assert OPACITY_PRECONDITION_STDERR in err


def test_set_tab_color_accepts_named_hex_NONE(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers tab_color_{named,hex,NONE}_accepted."""
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path, extra_lines=DYNAMIC_OPACITY_LINE)
    with spawn_kitty(conf, tmp_path) as pid:
        wait_for_socket(pid)
        time.sleep(0.4)
        pin_pgrep_to_pid(monkeypatch, pid)
        assert accent.set_tab_accent("blue") == 0
        assert accent.set_tab_accent("#0066cc") == 0
        assert accent.set_tab_accent("NONE") == 0


def test_set_tab_color_rejects_invalid_color(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Covers tab_color_invalid_rejected + tab_color_invalid_stderr_excerpt."""
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path, extra_lines=DYNAMIC_OPACITY_LINE)
    with spawn_kitty(conf, tmp_path) as pid:
        wait_for_socket(pid)
        time.sleep(0.4)
        pin_pgrep_to_pid(monkeypatch, pid)
        rc = accent.set_tab_accent("notacolor")
    assert rc != 0
    err = capsys.readouterr().err
    assert "is not a valid color" in err


def test_set_colors_isolates_to_matched_pane(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers launch_second_pane_ok, pane_count_after_launch, set_colors_per_pane_ok,
    pane_a_background_after, pane_b_background_after.
    """
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path, extra_lines=DYNAMIC_OPACITY_LINE)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        pin_pgrep_to_pid(monkeypatch, pid)

        # Launch a second pane (kitty "window") in the active tab.
        launch = kitten_call(socket, "launch", "--type=window", "--no-response")
        assert launch.returncode == 0, f"launch failed: {launch.stderr!r}"
        time.sleep(0.4)

        # Probe-grounded: exactly 2 panes after launch.
        windows = [
            w for ostab in ls(socket) for tab in ostab["tabs"] for w in tab["windows"]
        ]
        assert len(windows) == 2, f"expected 2 panes, got {len(windows)}: {windows!r}"
        a_id = windows[0]["id"]
        b_id = windows[1]["id"]

        # Drive the scene function to set bg on pane A only.
        rc = background.set_window_background("#001a33", match=f"id:{a_id}")
        assert rc == 0
        time.sleep(0.2)

        # Per-pane isolation: pane A changed, pane B unchanged.
        assert get_color(socket, "background", f"id:{a_id}") == "#001a33"
        assert get_color(socket, "background", f"id:{b_id}") == "#000000"


def test_set_colors_accepts_named_color(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers set_colors_named_ok + pane_b_background_named.

    Named color `darkblue` resolves via kitty's X11 rgb.txt table to `#00008b`.
    """
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path, extra_lines=DYNAMIC_OPACITY_LINE)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        pin_pgrep_to_pid(monkeypatch, pid)
        rc = background.set_window_background("darkblue")
        assert rc == 0
        time.sleep(0.2)
        assert get_color(socket, "background") == "#00008b"


def test_set_font_size_absolute_relative_reset(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers font_set_14_ok, font_set_plus2_ok, font_set_reset_ok.

    kitten @ ls does NOT expose font_size, so exit code is the only observable.
    Visual outcome is covered by docs/repro/h23-styling.md.
    """
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path, extra_lines=DYNAMIC_OPACITY_LINE)
    with spawn_kitty(conf, tmp_path) as pid:
        wait_for_socket(pid)
        time.sleep(0.4)
        pin_pgrep_to_pid(monkeypatch, pid)
        assert font.set_os_window_font_size("14") == 0
        time.sleep(0.2)
        assert font.set_os_window_font_size("+2") == 0
        time.sleep(0.2)
        assert font.set_os_window_font_size("0") == 0


def test_set_opacity_reflected_in_ls_with_tolerance(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Covers opacity_set_ok + opacity_in_ls_after_set (with precision tolerance).

    Per D4: kitty stores opacity as a float32-ish value, so 0.7 round-trips as
    0.699999988079071 in `kitten @ ls`. The implementation MUST compare with
    tolerance, not equality — the comparison below IS the test (per tasks
    §6.1.1's mapping for `opacity_ls_precision_note`).
    """
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path, extra_lines=DYNAMIC_OPACITY_LINE)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        pin_pgrep_to_pid(monkeypatch, pid)
        assert opacity.set_os_window_opacity(0.7) == 0
        time.sleep(0.3)
        ls_after = ls(socket)
        actual = ls_after[0].get("background_opacity")
        assert actual is not None
        assert abs(actual - 0.7) < 0.01, f"opacity {actual!r} not within 0.01 of 0.7"


def test_set_opacity_toggle_resets_to_default(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Covers opacity_toggle_ok, opacity_toggle_stderr_excerpt, opacity_in_ls_after_toggle.

    Probe-grounded: setting 0.7, then calling --toggle 0.7, returns the window
    to kitty default opacity (1.0). Empty stderr on success.
    """
    stub_config(monkeypatch, tmp_path)
    conf = draft_conf(tmp_path, extra_lines=DYNAMIC_OPACITY_LINE)
    with spawn_kitty(conf, tmp_path) as pid:
        socket = wait_for_socket(pid)
        time.sleep(0.4)
        pin_pgrep_to_pid(monkeypatch, pid)
        assert opacity.set_os_window_opacity(0.7) == 0
        time.sleep(0.3)
        capsys.readouterr()  # drain the set-call stderr (should be empty)
        assert opacity.set_os_window_opacity(0.7, toggle=True) == 0
        # On success the scene wrapper does not write to sys.stderr; capsys.err empty.
        assert capsys.readouterr().err == ""
        time.sleep(0.3)
        ls_after_toggle = ls(socket)
        assert ls_after_toggle[0].get("background_opacity") == 1.0
