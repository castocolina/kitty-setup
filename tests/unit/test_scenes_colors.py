"""Unit tests for kitty_setup.scenes.colors (Phase 2 / friendly-color-input)."""

from __future__ import annotations

import argparse
import subprocess

import pytest

from kitty_setup.scenes import accent, background, launcher
from kitty_setup.scenes.colors import ColorError, normalize_color

# --------------------------------------------------------------------------- #
# 3.1 — hashless / short hex
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("fff", "#fff"),
        ("000", "#000"),
        ("ffffff", "#ffffff"),
        ("1A2B3C", "#1a2b3c"),
        ("#fff", "#fff"),
        ("#001F3F", "#001f3f"),
        ("0a7", "#0a7"),
    ],
)
def test_hex_normalisation(value: str, expected: str) -> None:
    assert normalize_color(value) == expected


@pytest.mark.parametrize("value", ["#ffzz", "abcd", "12345", "#12", "ggg"])
def test_not_hex_falls_through_to_name_or_error(value: str) -> None:
    # 4/5-char or non-hex-digit tokens are NOT treated as hex; none are names.
    with pytest.raises(ColorError):
        normalize_color(value)


# --------------------------------------------------------------------------- #
# 3.2 — name translation (the gap kitty rejects natively)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "hexv"),
    [
        ("teal", "#008080"),
        ("olive", "#808000"),
        ("lime", "#00ff00"),
        ("aqua", "#00ffff"),
        ("indigo", "#4b0082"),
        ("crimson", "#dc143c"),
        ("silver", "#c0c0c0"),
        ("fuchsia", "#ff00ff"),
        ("rebeccapurple", "#663399"),
    ],
)
def test_gap_name_translates_to_hex(name: str, hexv: str) -> None:
    assert normalize_color(name) == hexv


def test_name_lookup_is_case_insensitive() -> None:
    assert normalize_color("Teal") == "#008080"
    assert normalize_color("OLIVE") == "#808000"


# --------------------------------------------------------------------------- #
# 3.3 — collision-free known names (X11 wins, no CSS tone regression)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "x11_hex"),
    [
        ("green", "#00ff00"),  # NOT the CSS #008000
        ("gray", "#bebebe"),  # NOT the CSS #808080
        ("grey", "#bebebe"),
        ("purple", "#a020f0"),  # NOT the CSS #800080
        ("maroon", "#b03060"),  # NOT the CSS #800000
        ("navy", "#000080"),
        ("orange", "#ffa500"),
    ],
)
def test_known_name_keeps_x11_value(name: str, x11_hex: str) -> None:
    assert normalize_color(name) == x11_hex


def test_gray_and_grey_spellings_agree() -> None:
    assert normalize_color("grey") == normalize_color("gray")
    assert normalize_color("grey50") == normalize_color("gray50")


# --------------------------------------------------------------------------- #
# 3.4 / 3.5 — passthrough sentinels + empty
# --------------------------------------------------------------------------- #


def test_none_sentinel_passes_through() -> None:
    assert normalize_color("NONE") == "NONE"
    assert normalize_color("none") == "NONE"


def test_functional_and_rgb_forms_pass_through() -> None:
    assert normalize_color("rgb:00/ff/00") == "rgb:00/ff/00"
    assert normalize_color("rgba(1,2,3,0.5)") == "rgba(1,2,3,0.5)"


def test_empty_and_none_become_absent() -> None:
    assert normalize_color("") is None
    assert normalize_color("   ") is None
    assert normalize_color(None) is None


# --------------------------------------------------------------------------- #
# 3.6 — unknown -> ColorError with an actionable message
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("value", ["notacolor", "rebeccapurpel", "blu", "#ffzz"])
def test_unknown_raises_colorerror_naming_the_value(value: str) -> None:
    with pytest.raises(ColorError) as exc:
        normalize_color(value)
    msg = str(exc.value)
    assert repr(value) in msg
    assert "hex" in msg and "teal" in msg  # shows a hex AND a name example


def test_colorerror_is_a_valueerror() -> None:
    assert issubclass(ColorError, ValueError)


# --------------------------------------------------------------------------- #
# 3.7 — per-site mapping: no kitten call on a bad color
# --------------------------------------------------------------------------- #


def _boom(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
    raise AssertionError("kitten_at must NOT be called for an invalid color")


def test_tab_accent_rejects_bad_color_before_kitten(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(accent._client, "kitten_at", _boom)
    rc = accent.cli_set_tab_accent(
        argparse.Namespace(color="notacolor", active_fg=None, inactive_fg=None, match=None, to=None)
    )
    assert rc == 1
    assert "not a recognized color" in capsys.readouterr().err


def test_window_background_rejects_bad_color_before_kitten(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(background._client, "kitten_at", _boom)
    rc = background.cli_set_window_background(
        argparse.Namespace(color="notacolor", match=None, to=None)
    )
    assert rc == 1
    assert "not a recognized color" in capsys.readouterr().err


def test_scene_rejects_bad_color_before_any_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    # launch_scene normalizes every color up front; a bad bg raises ColorError
    # BEFORE the first kitten call (no window opens).
    monkeypatch.setattr(launcher._client, "kitten_at", _boom)
    with pytest.raises(ColorError):
        launcher.launch_scene(
            layout="tall",
            tab_title="x",
            tab_accent="#fff",
            panes=[
                launcher.Pane(title="p1"),
                launcher.Pane(title="p2", bg="notacolor"),
            ],
        )


def test_scene_bg_name_is_normalised_in_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def rec(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        calls.append((verb, *args))
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="101\n", stderr="")

    monkeypatch.setattr(launcher._client, "kitten_at", rec)
    # Single-pane scene with a gap name as bg -> set-colors carries the hex.
    launcher.launch_scene(None, None, None, [launcher.Pane(title="solo", bg="teal")])
    setcolors = next(c for c in calls if c[0] == "set-colors")
    assert "background=#008080" in setcolors
