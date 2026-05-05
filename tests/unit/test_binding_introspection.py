"""Unit tests for ``kitty_setup.binding_introspection``.

The pure helpers (`_walk_payload`, `_read_allow_list`, `_classify`,
`Report.render_text`, `Report.to_json`) are exercised against synthetic input.
The `kitty +runpy` shell-out (`_run_kitty_runpy`) and `enumerate_bindings`
end-to-end are exercised by the integration test under
``tests/integration/test_h03_introspection.py`` per R7.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kitty_setup import binding_introspection as bi

# ---- helpers --------------------------------------------------------------


def _payload(tmp_path: Path, name: str, lines: str) -> Path:
    f = tmp_path / name
    f.write_text(lines, encoding="utf-8")
    return f


# ---- _walk_payload --------------------------------------------------------


def test_walk_payload_empty_dir(tmp_path: Path) -> None:
    assert bi._walk_payload(tmp_path) == {}


def test_walk_payload_missing_dir(tmp_path: Path) -> None:
    assert bi._walk_payload(tmp_path / "no-such") == {}


def test_walk_payload_extracts_chord_action_pairs(tmp_path: Path) -> None:
    _payload(
        tmp_path,
        "windowing.conf",
        "# header\nmap ctrl+shift+t launch --type=tab --cwd=current\n"
        "map ctrl+shift+\\ launch --location=vsplit --cwd=current\n",
    )
    _payload(tmp_path, "bindings.conf", "map ctrl+shift+k clear_terminal scrollback active\n")
    result = bi._walk_payload(tmp_path)
    assert result == {
        ("ctrl+shift+t", "launch --type=tab --cwd=current"): "windowing",
        ("ctrl+shift+\\", "launch --location=vsplit --cwd=current"): "windowing",
        ("ctrl+shift+k", "clear_terminal scrollback active"): "bindings",
    }


def test_walk_payload_skips_kitty_setup_and_overrides(tmp_path: Path) -> None:
    _payload(tmp_path, "kitty-setup.conf", "include windowing.conf\n")
    _payload(tmp_path, "intentional-overrides.conf", "ctrl+shift+t\n")
    _payload(tmp_path, "windowing.conf", "map ctrl+shift+t launch --type=tab\n")
    result = bi._walk_payload(tmp_path)
    assert result == {("ctrl+shift+t", "launch --type=tab"): "windowing"}


def test_walk_payload_ignores_non_map_lines(tmp_path: Path) -> None:
    _payload(
        tmp_path,
        "x.conf",
        "# comment\n\nfont_size 12\nmap ctrl+a copy_to_clipboard\nuwu garbage line\n",
    )
    assert bi._walk_payload(tmp_path) == {("ctrl+a", "copy_to_clipboard"): "x"}


# ---- _read_allow_list -----------------------------------------------------


def test_read_allow_list_missing_file(tmp_path: Path) -> None:
    assert bi._read_allow_list(tmp_path / "no-such") == set()


def test_read_allow_list_basic(tmp_path: Path) -> None:
    f = tmp_path / "allow"
    f.write_text("# header\n\nctrl+shift+t\nctrl+shift+n   # inline comment\n#commented\n")
    assert bi._read_allow_list(f) == {"ctrl+shift+t", "ctrl+shift+n"}


# ---- _classify ------------------------------------------------------------


def _entry(chord: str, action: str) -> dict[str, str]:
    return {"chord": chord, "action": action}


def test_classify_no_collisions() -> None:
    raw = [
        _entry("ctrl+shift+\\", "launch --location=vsplit --cwd=current"),
        _entry("ctrl+a", "copy_to_clipboard"),
    ]
    payload = {("ctrl+shift+\\", "launch --location=vsplit --cwd=current"): "windowing"}
    bindings, ours, defaults, conflicts = bi._classify(raw, payload, set())
    assert ours == 1
    assert defaults == 1
    assert conflicts == 0
    sources = {b.source for b in bindings}
    assert sources == {"windowing", bi.DEFAULT_SOURCE}
    assert all(b.conflicts_with == () for b in bindings)
    assert all(b.override_of is None for b in bindings)


def test_classify_intentional_override() -> None:
    raw = [
        _entry("ctrl+shift+t", "new_tab"),  # kitty default
        _entry("ctrl+shift+t", "launch --type=tab --cwd=current"),  # ours
    ]
    payload = {("ctrl+shift+t", "launch --type=tab --cwd=current"): "windowing"}
    allow = {"ctrl+shift+t"}
    bindings, ours, defaults, conflicts = bi._classify(raw, payload, allow)
    assert ours == 1
    assert defaults == 1
    assert conflicts == 0
    ours_binding = next(b for b in bindings if b.source == "windowing")
    assert ours_binding.override_of == "new_tab"
    assert ours_binding.conflicts_with == ()
    default_binding = next(b for b in bindings if b.source == bi.DEFAULT_SOURCE)
    assert default_binding.override_of is None
    assert default_binding.conflicts_with == ()


def test_classify_unauthorised_shadow_is_conflict() -> None:
    raw = [
        _entry("ctrl+shift+-", "change_font_size all -2.0"),  # kitty default
        _entry("ctrl+shift+-", "launch --location=hsplit --cwd=current"),  # ours
    ]
    payload = {("ctrl+shift+-", "launch --location=hsplit --cwd=current"): "windowing"}
    allow: set[str] = set()  # NOT allow-listed
    bindings, ours, defaults, conflicts = bi._classify(raw, payload, allow)
    assert ours == 1
    assert defaults == 1
    assert conflicts == 1
    ours_binding = next(b for b in bindings if b.source == "windowing")
    assert ours_binding.override_of is None
    assert any("kitty default change_font_size" in c for c in ours_binding.conflicts_with)
    default_binding = next(b for b in bindings if b.source == bi.DEFAULT_SOURCE)
    assert default_binding.conflicts_with == ()


def test_classify_two_of_ours_collide() -> None:
    raw = [
        _entry("ctrl+x", "copy_to_clipboard"),
        _entry("ctrl+x", "paste_from_clipboard"),
    ]
    payload = {
        ("ctrl+x", "copy_to_clipboard"): "windowing",
        ("ctrl+x", "paste_from_clipboard"): "bindings",
    }
    allow = {"ctrl+x"}  # even allow-listed: two ours = conflict
    bindings, ours, defaults, conflicts = bi._classify(raw, payload, allow)
    assert ours == 2
    assert defaults == 0
    assert conflicts == 1
    for b in bindings:
        assert any("also in" in c for c in b.conflicts_with)


def test_classify_three_or_more_defs_is_conflict_regardless_of_allow_list() -> None:
    raw = [
        _entry("ctrl+shift+t", "new_tab"),
        _entry("ctrl+shift+t", "launch --type=tab --cwd=current"),
        _entry("ctrl+shift+t", "launch --type=tab --location=after"),
    ]
    payload = {
        ("ctrl+shift+t", "launch --type=tab --cwd=current"): "windowing",
        ("ctrl+shift+t", "launch --type=tab --location=after"): "extras",
    }
    allow = {"ctrl+shift+t"}
    _b, _o, _d, conflicts = bi._classify(raw, payload, allow)
    assert conflicts == 1


# ---- Report rendering -----------------------------------------------------


def _make_report(bindings: list[bi.Binding], conflicts: int = 0) -> bi.Report:
    ours = sum(1 for b in bindings if b.source != bi.DEFAULT_SOURCE)
    defaults = sum(1 for b in bindings if b.source == bi.DEFAULT_SOURCE)
    return bi.Report(
        bindings=tuple(bindings),
        ours_count=ours,
        defaults_count=defaults,
        conflicts_count=conflicts,
    )


def test_render_text_groups_by_source() -> None:
    report = _make_report(
        [
            bi.Binding("ctrl+shift+t", "launch --type=tab --cwd=current", "windowing", "new_tab"),
            bi.Binding("ctrl+shift+k", "clear", "bindings"),
            bi.Binding("ctrl+c", "copy", bi.DEFAULT_SOURCE),
        ]
    )
    text = report.render_text()
    assert "bindings (1 bindings)" in text
    assert "windowing (1 bindings)" in text
    assert "kitty defaults (1 bindings)" in text
    # Default section appears LAST.
    assert text.index("kitty defaults") > text.index("windowing")
    assert text.index("kitty defaults") > text.index("bindings (1 bindings)")
    assert "[overrides default new_tab]" in text
    assert "Summary: 2 ours, 1 defaults, 0 conflicts." in text


def test_render_text_singular_conflict() -> None:
    report = _make_report(
        [bi.Binding("ctrl+shift+-", "x", "windowing", conflicts_with=("kitty default y",))],
        conflicts=1,
    )
    assert "1 conflict." in report.render_text()
    assert "[CONFLICT: kitty default y]" in report.render_text()


def test_to_json_round_trip() -> None:
    report = _make_report(
        [
            bi.Binding("a", "act", "windowing", "default"),
            bi.Binding("b", "act2", bi.DEFAULT_SOURCE),
        ],
        conflicts=0,
    )
    payload = json.loads(report.to_json())
    assert payload["summary"] == {"ours": 1, "defaults": 1, "conflicts": 0}
    assert {b["source"] for b in payload["bindings"]} == {"windowing", bi.DEFAULT_SOURCE}
    assert payload["bindings"][0]["override_of"] == "default"


# ---- cli_keys + error path ------------------------------------------------


def test_cli_keys_text_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = _make_report([bi.Binding("ctrl+shift+t", "x", "windowing", "default")])
    monkeypatch.setattr(bi, "enumerate_bindings", lambda *a, **kw: fake)
    args = type("A", (), {"json": False, "config_path": "/tmp/dummy"})()
    code = bi.cli_keys(args)  # type: ignore[arg-type]
    out = capsys.readouterr().out
    assert code == 0
    assert "windowing" in out
    assert "Summary:" in out


def test_cli_keys_json_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = _make_report([bi.Binding("ctrl+shift+t", "x", "windowing")])
    monkeypatch.setattr(bi, "enumerate_bindings", lambda *a, **kw: fake)
    args = type("A", (), {"json": True, "config_path": None})()
    code = bi.cli_keys(args)  # type: ignore[arg-type]
    out = capsys.readouterr().out
    assert code == 0
    parsed = json.loads(out)
    assert parsed["summary"]["ours"] == 1


def test_cli_keys_returns_non_zero_on_introspection_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*_a: object, **_k: object) -> bi.Report:
        raise bi.BindingIntrospectionError("kitty missing")

    monkeypatch.setattr(bi, "enumerate_bindings", boom)
    args = type("A", (), {"json": False, "config_path": None})()
    code = bi.cli_keys(args)  # type: ignore[arg-type]
    err = capsys.readouterr().err
    assert code == 1
    assert "kitty missing" in err
