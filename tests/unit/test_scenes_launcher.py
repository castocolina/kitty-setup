"""Unit tests for kitty_setup.scenes.launcher (Phase 2 §12)."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Iterable

import pytest

from kitty_setup.scenes import launcher
from kitty_setup.scenes._client import SceneClientError


def _ok(stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr=stderr)


def _err(returncode: int = 1, stderr: str = "boom\n") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=stderr)


class _Recorder:
    """Records every kitten_at call's argv+kwargs and returns scripted results."""

    def __init__(self, results: Iterable[subprocess.CompletedProcess[str]]) -> None:
        self.results = list(results)
        self.calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def __call__(
        self, verb: str, *args: str, to: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(((verb, *args), {"to": to}))
        if not self.results:
            raise AssertionError(f"Recorder exhausted; unexpected extra call: {verb=} {args=}")
        return self.results.pop(0)


# --------------------------------------------------------------------------- #
# 4.2 — parse_pane_spec happy paths
# --------------------------------------------------------------------------- #


def test_parse_single_key() -> None:
    assert launcher.parse_pane_spec("title=docker") == launcher.Pane(title="docker")


def test_parse_multiple_keys() -> None:
    result = launcher.parse_pane_spec("title=docker,cmd=docker ps,cwd=/srv,bg=#001f3f")
    assert result == launcher.Pane(title="docker", cmd="docker ps", cwd="/srv", bg="#001f3f")


def test_parse_value_contains_equals() -> None:
    result = launcher.parse_pane_spec("cmd=docker run --env VAR=value bash")
    assert result.cmd == "docker run --env VAR=value bash"


def test_parse_escaped_comma() -> None:
    result = launcher.parse_pane_spec("title=a\\,b,cmd=echo")
    assert result.title == "a,b"
    assert result.cmd == "echo"


def test_parse_escaped_backslash() -> None:
    result = launcher.parse_pane_spec("title=a\\\\b")
    assert result.title == "a\\b"


def test_parse_empty_value_yields_none_not_empty_string() -> None:
    result = launcher.parse_pane_spec("title=,cmd=echo")
    assert result.title is None  # empty value normalises to None
    assert result.cmd == "echo"
    assert result.cwd is None
    assert result.bg is None


# --------------------------------------------------------------------------- #
# 4.3 — parse_pane_spec error paths
# --------------------------------------------------------------------------- #


def test_parse_empty_input_raises() -> None:
    with pytest.raises(ValueError, match="empty pane spec"):
        launcher.parse_pane_spec("")


def test_parse_segment_without_equals_raises() -> None:
    with pytest.raises(ValueError, match="malformed pane spec"):
        launcher.parse_pane_spec("title")


def test_parse_duplicate_key_raises() -> None:
    with pytest.raises(ValueError, match="duplicate key 'title'"):
        launcher.parse_pane_spec("title=a,title=b")


def test_parse_trailing_comma_raises() -> None:
    with pytest.raises(ValueError, match="empty segment"):
        launcher.parse_pane_spec("title=a,")


def test_parse_unknown_key_names_offender_and_lists_recognised() -> None:
    with pytest.raises(ValueError) as exc_info:
        launcher.parse_pane_spec("tile=docker")
    message = str(exc_info.value)
    assert "tile" in message
    assert "title" in message and "cmd" in message and "cwd" in message and "bg" in message


# --------------------------------------------------------------------------- #
# 4.4 — launch_scene argv composition (golden against h25 probe Q5)
# --------------------------------------------------------------------------- #


def test_launch_scene_argv_matches_h25_q5_six_call_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _Recorder(
        [
            _ok(stdout="101\n"),  # launch --type=tab → win0 (p0 has no bg)
            _ok(),  # goto-layout (focused tab)
            _ok(stdout="102\n"),  # launch --type=window for p1
            _ok(),  # set-colors for p1.bg
            _ok(stdout="103\n"),  # launch --type=window for p2 (no bg)
            _ok(),  # set-tab-color for tab accent
        ]
    )
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    panes = [
        launcher.Pane(title="p1", cmd="echo p1"),
        launcher.Pane(title="p2", bg="#001f3f", cmd="echo p2"),
        launcher.Pane(title="p3"),
    ]
    rc = launcher.launch_scene(
        layout="tall:mirrored=true",
        tab_title="🐳 mon",
        tab_accent="#ff851b",
        panes=panes,
    )
    assert rc == 0
    assert len(recorder.calls) == 6  # mirrors h25 Q5_kitten_call_count

    call_verbs = [c[0][0] for c in recorder.calls]
    assert call_verbs == [
        "launch",
        "goto-layout",
        "launch",
        "set-colors",
        "launch",
        "set-tab-color",
    ]

    tab_launch = recorder.calls[0][0]
    assert "--type=tab" in tab_launch
    assert "--hold" in tab_launch
    assert "--tab-title=🐳 mon" in tab_launch
    assert "--title=p1" in tab_launch
    assert "bash" in tab_launch and "-lc" in tab_launch and "echo p1" in tab_launch

    goto_layout = recorder.calls[1][0]
    assert goto_layout == ("goto-layout", "tall:mirrored=true")

    p1_launch = recorder.calls[2][0]
    assert "--type=window" in p1_launch
    assert "--hold" in p1_launch
    assert "--title=p2" in p1_launch
    assert "bash" in p1_launch and "-lc" in p1_launch and "echo p2" in p1_launch

    p1_bg = recorder.calls[3][0]
    assert p1_bg == ("set-colors", "--match", "id:102", "background=#001f3f")

    p2_launch = recorder.calls[4][0]
    assert "--type=window" in p2_launch
    assert "--title=p3" in p2_launch
    assert "bash" not in p2_launch  # no cmd on p3

    accent = recorder.calls[5][0]
    assert accent == (
        "set-tab-color",
        "--match",
        "recent:0",
        "active_bg=#ff851b",
        "inactive_bg=#ff851b",
    )


def test_launch_scene_accent_uses_recent_zero_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Tab accent only applies to a multi-pane scene (which opens a new tab).
    recorder = _Recorder([_ok(stdout="101\n"), _ok(stdout="102\n"), _ok()])
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    launcher.launch_scene(
        layout=None,
        tab_title=None,
        tab_accent="#ff851b",
        panes=[launcher.Pane(title="p1"), launcher.Pane(title="p2")],
    )
    assert len(recorder.calls) == 3
    accent_call = recorder.calls[2][0]
    assert accent_call == (
        "set-tab-color",
        "--match",
        "recent:0",
        "active_bg=#ff851b",
        "inactive_bg=#ff851b",
    )


# --------------------------------------------------------------------------- #
# Single-pane scene → current tab; launch-dir cwd default
# --------------------------------------------------------------------------- #


def test_single_pane_launches_window_into_current_tab(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # One pane → exactly one `launch --type=window`; tab title/layout/accent are
    # NOT applied (the window joins the current tab, there is no new tab to style).
    recorder = _Recorder([_ok(stdout="101\n")])
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    rc = launcher.launch_scene(
        layout="tall",
        tab_title="ignored",
        tab_accent="#ff851b",
        panes=[launcher.Pane(title="solo", cmd="echo hi")],
    )
    assert rc == 0
    assert len(recorder.calls) == 1
    argv = recorder.calls[0][0]
    assert argv[0] == "launch"
    assert "--type=window" in argv
    assert "--type=tab" not in argv
    assert not any(a.startswith("--tab-title") for a in argv)
    assert "--title=solo" in argv


def test_single_pane_with_bg_still_styles_the_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _Recorder([_ok(stdout="101\n"), _ok()])
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    launcher.launch_scene(
        layout=None,
        tab_title=None,
        tab_accent=None,
        panes=[launcher.Pane(title="solo", bg="#001f3f")],
    )
    assert len(recorder.calls) == 2
    assert recorder.calls[1][0] == ("set-colors", "--match", "id:101", "background=#001f3f")


def test_default_cwd_applies_to_panes_without_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _Recorder([_ok(stdout="101\n"), _ok(stdout="102\n")])
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    launcher.launch_scene(
        layout=None,
        tab_title=None,
        tab_accent=None,
        panes=[launcher.Pane(title="p1"), launcher.Pane(title="p2")],
        default_cwd="/work/proj",
    )
    # Both the tab's first window and the additional window inherit the launch dir.
    assert "--cwd=/work/proj" in recorder.calls[0][0]
    assert "--cwd=/work/proj" in recorder.calls[1][0]


def test_pane_cwd_overrides_default_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _Recorder([_ok(stdout="101\n")])
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    launcher.launch_scene(
        layout=None,
        tab_title=None,
        tab_accent=None,
        panes=[launcher.Pane(title="solo", cwd="/explicit")],
        default_cwd="/work/proj",
    )
    argv = recorder.calls[0][0]
    assert "--cwd=/explicit" in argv
    assert "--cwd=/work/proj" not in argv


def test_multipane_with_origin_window_fills_current_tab(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Inside kitty ($KITTY_WINDOW_ID present), a multi-pane scene fills the
    # CURRENT tab: pane 0 reuses the origin window (restyled in place), the rest
    # open as splits, and layout/tab-title/tab-accent target the focused tab
    # (no --type=tab, no recent:0).
    recorder = _Recorder(
        [
            _ok(_ls_json([7])),  # ls: origin tab is solo (only window 7)
            _ok(),  # set-window-title (pane0)
            _ok(stdout="201\n"),  # launch git
            _ok(),  # set-colors git bg
            _ok(stdout="202\n"),  # launch watch
            _ok(),  # goto-layout
            _ok(),  # set-tab-title
            _ok(),  # set-tab-color
        ]
    )
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    rc = launcher.launch_scene(
        layout="tall",
        tab_title="🛠️ dev",
        tab_accent="#2ecc40",
        panes=[
            launcher.Pane(title="shell"),
            launcher.Pane(title="git", bg="#0b1f0b"),
            launcher.Pane(title="watch"),
        ],
        origin_window=7,
    )
    assert rc == 0
    verbs = [c[0][0] for c in recorder.calls]
    assert verbs == [
        "ls",  # solo-tab check precedes the fill
        "set-window-title",
        "launch",
        "set-colors",
        "launch",
        "goto-layout",
        "set-tab-title",
        "set-tab-color",
    ]
    # Pane 0 reuses the origin window; no new tab is ever requested.
    assert recorder.calls[1][0] == ("set-window-title", "--match", "id:7", "shell")
    assert all("--type=tab" not in c[0] for c in recorder.calls)
    # Tab styling targets the focused tab — no recent:0 match.
    assert recorder.calls[-1][0] == (
        "set-tab-color",
        "active_bg=#2ecc40",
        "inactive_bg=#2ecc40",
    )


def test_origin_window_ignored_for_single_pane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A single-pane scene keeps its window-into-current-tab behavior even inside
    # kitty — it does not commandeer the origin shell.
    recorder = _Recorder([_ok(stdout="101\n")])
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    launcher.launch_scene(
        layout="tall",
        tab_title="ignored",
        tab_accent="#ff851b",
        panes=[launcher.Pane(title="solo")],
        origin_window=7,
    )
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0][0] == "launch"
    assert "--type=window" in recorder.calls[0][0]


# --------------------------------------------------------------------------- #
# 4.5 — launch_scene error paths
# --------------------------------------------------------------------------- #


def test_launch_failure_aborts_and_propagates_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _Recorder([_err(returncode=7, stderr="kitten broke\n")])
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    rc = launcher.launch_scene(
        layout="tall",
        tab_title="x",
        tab_accent="#fff",
        panes=[launcher.Pane(title="p1", cmd="echo")],
    )
    assert rc == 7
    assert len(recorder.calls) == 1  # aborted after first failure; no goto-layout, no accent


def test_set_colors_failure_is_soft_and_remaining_calls_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _Recorder(
        [
            _ok(stdout="101\n"),  # tab launch ok
            _err(returncode=3, stderr="badcol"),  # set-colors fails
            _ok(),  # goto-layout still runs
            _ok(stdout="102\n"),  # second pane launch
            _ok(),  # tab accent
        ]
    )
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    rc = launcher.launch_scene(
        layout="tall",
        tab_title="x",
        tab_accent="#fff",
        panes=[
            launcher.Pane(title="p1", bg="#001f3f"),
            launcher.Pane(title="p2"),
        ],
    )
    assert rc == 3  # first non-zero propagates (set-colors fails soft)
    assert len(recorder.calls) == 5  # all 5 calls executed; soft-fail did not abort


# --------------------------------------------------------------------------- #
# 4.6 — cli_scene_launch error paths
# --------------------------------------------------------------------------- #


def _ns(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "layout": None,
        "tab_title": None,
        "tab_accent": None,
        "panes": [],
        "to": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_cli_zero_panes_exits_1_with_clear_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = launcher.cli_scene_launch(_ns(panes=[]))
    assert rc == 1
    captured = capsys.readouterr()
    assert "at least one --pane" in captured.err


def test_cli_parser_error_exits_1_and_stderr_names_offender(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sentinel = _Recorder([])
    monkeypatch.setattr(launcher._client, "kitten_at", sentinel)

    rc = launcher.cli_scene_launch(_ns(panes=["tile=docker"]))
    assert rc == 1
    captured = capsys.readouterr()
    assert "tile" in captured.err
    assert sentinel.calls == []  # never reached kitten


def test_cli_scene_client_error_surfaces_with_exit_1(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _raise(*_args: object, **_kwargs: object) -> object:
        raise SceneClientError("no kitty process found")

    monkeypatch.setattr(launcher._client, "kitten_at", _raise)

    rc = launcher.cli_scene_launch(_ns(panes=["title=ok"]))
    assert rc == 1
    captured = capsys.readouterr()
    assert "no kitty process found" in captured.err


# --------------------------------------------------------------------------- #
# phase2-scene-polish #2 — _origin_tab_is_solo (fill current tab only if solo)
# --------------------------------------------------------------------------- #


def _ls_json(*tabs_window_ids: list[int]) -> str:
    """Build a `kitten @ ls` JSON tree: one OS window, one tab per id-list."""
    tabs = [{"windows": [{"id": wid} for wid in ids]} for ids in tabs_window_ids]
    return json.dumps([{"tabs": tabs}])


def test_origin_tab_is_solo_true_for_single_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher._client, "kitten_at", lambda *a, **k: _ok(_ls_json([7])))
    assert launcher._origin_tab_is_solo(7, None) is True


def test_origin_tab_is_solo_false_for_two_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    # Origin window 7 shares its tab with window 8 -> not solo.
    monkeypatch.setattr(launcher._client, "kitten_at", lambda *a, **k: _ok(_ls_json([7, 8])))
    assert launcher._origin_tab_is_solo(7, None) is False


def test_origin_tab_is_solo_false_when_origin_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    # The origin id is in a different tab's window set than queried -> still found
    # there; but if absent everywhere, fail-safe False.
    monkeypatch.setattr(launcher._client, "kitten_at", lambda *a, **k: _ok(_ls_json([1], [2, 3])))
    assert launcher._origin_tab_is_solo(99, None) is False


def test_origin_tab_is_solo_false_on_ls_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher._client, "kitten_at", lambda *a, **k: _err())
    assert launcher._origin_tab_is_solo(7, None) is False


def test_origin_tab_is_solo_false_on_garbage_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher._client, "kitten_at", lambda *a, **k: _ok("not json{"))
    assert launcher._origin_tab_is_solo(7, None) is False


def test_origin_tab_is_solo_finds_the_right_tab(monkeypatch: pytest.MonkeyPatch) -> None:
    # Origin 5 sits in a solo tab even though another tab has two windows.
    monkeypatch.setattr(launcher._client, "kitten_at", lambda *a, **k: _ok(_ls_json([2, 3], [5])))
    assert launcher._origin_tab_is_solo(5, None) is True


def test_multipane_with_origin_but_nonsolo_tab_opens_new_tab(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Inside kitty but the origin tab already holds 2 windows -> do NOT fill it;
    # fall through to the new-tab path (launch --type=tab + recent:0 accent).
    recorder = _Recorder(
        [
            _ok(_ls_json([7, 8])),  # ls: origin tab is NOT solo
            _ok(stdout="300\n"),  # launch p0 as a new TAB
            _ok(),  # goto-layout
            _ok(stdout="301\n"),  # launch git (window)
            _ok(),  # set-colors git bg
            _ok(stdout="302\n"),  # launch watch (window)
            _ok(),  # set-tab-color recent:0
        ]
    )
    monkeypatch.setattr(launcher._client, "kitten_at", recorder)

    rc = launcher.launch_scene(
        layout="tall",
        tab_title="DEV",
        tab_accent="#2ecc40",
        panes=[
            launcher.Pane(title="shell"),
            launcher.Pane(title="git", bg="#0b1f0b"),
            launcher.Pane(title="watch"),
        ],
        origin_window=7,
    )
    assert rc == 0
    verbs = [c[0][0] for c in recorder.calls]
    assert verbs[0] == "ls"
    # The first pane opened a NEW tab (not a reused origin window).
    assert "--type=tab" in recorder.calls[1][0]
    assert all(c[0][0] != "set-window-title" for c in recorder.calls)
    # New-tab accent targets recent:0 (not the focused-tab default).
    assert recorder.calls[-1][0] == (
        "set-tab-color",
        "--match",
        "recent:0",
        "active_bg=#2ecc40",
        "inactive_bg=#2ecc40",
    )
