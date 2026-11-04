"""Unit tests for the declarative scene recipe loader (Phase 2 §12 decl half).

Pure, host-independent: every test points the scenes directory at a tmp_path via
``$XDG_CONFIG_HOME`` and never spawns kitty. Covers schema validation, the
empty-string→None normalisation, the path-traversal guard, the available-scenes
hint, ``scene list`` output, and the ``cli_scene_launch`` mode-conflict
dispatch.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from kitty_setup.scenes import launcher, recipe
from kitty_setup.scenes.launcher import Pane


@pytest.fixture()
def scenes_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``scenes_dir()`` at ``tmp_path/kitty-setup/scenes`` and create it."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    scenes = tmp_path / "kitty-setup" / "scenes"
    scenes.mkdir(parents=True)
    return scenes


def _write(scenes: Path, name: str, body: str) -> None:
    (scenes / f"{name}.toml").write_text(body, encoding="utf-8")


# --------------------------------------------------------------------------- #
# load_scene — happy paths
# --------------------------------------------------------------------------- #


def test_load_scene_full_schema_returns_exact_tuple(scenes_root: Path) -> None:
    _write(
        scenes_root,
        "monitoring",
        """
        layout = "tall:mirrored=true"
        tab_title = "🐳 mon"
        tab_accent = "#001f3f"

        [[pane]]
        title = "p1"
        cmd = "echo p1"

        [[pane]]
        title = "p2"
        bg = "#001f3f"
        cmd = "echo p2"

        [[pane]]
        title = "p3"
        """,
    )
    layout, tab_title, tab_accent, panes = recipe.load_scene("monitoring")
    assert layout == "tall:mirrored=true"
    assert tab_title == "🐳 mon"
    assert tab_accent == "#001f3f"
    assert panes == [
        Pane(title="p1", cmd="echo p1"),
        Pane(title="p2", cmd="echo p2", bg="#001f3f"),
        Pane(title="p3"),
    ]


def test_load_scene_panes_are_launcher_pane_instances(scenes_root: Path) -> None:
    _write(scenes_root, "demo", '[[pane]]\ntitle = "only"\n')
    _, _, _, panes = recipe.load_scene("demo")
    # The loader reuses the engine's Pane, never a parallel copy.
    assert all(isinstance(p, Pane) for p in panes)
    assert recipe.Pane is launcher.Pane


def test_load_scene_omitted_style_keys_are_none(scenes_root: Path) -> None:
    _write(scenes_root, "bare", '[[pane]]\ncmd = "echo hi"\n')
    layout, tab_title, tab_accent, panes = recipe.load_scene("bare")
    assert (layout, tab_title, tab_accent) == (None, None, None)
    assert panes == [Pane(cmd="echo hi")]


def test_empty_string_value_normalises_to_none(scenes_root: Path) -> None:
    _write(scenes_root, "blank", '[[pane]]\ntitle = ""\ncmd = "echo hi"\n')
    _, _, _, panes = recipe.load_scene("blank")
    assert panes[0].title is None  # not ""
    assert panes[0].cmd == "echo hi"


# --------------------------------------------------------------------------- #
# load_scene — schema errors
# --------------------------------------------------------------------------- #


def test_unknown_top_level_key_is_rejected(scenes_root: Path) -> None:
    _write(scenes_root, "bad", 'tab_color = "#fff"\n[[pane]]\ntitle = "x"\n')
    with pytest.raises(recipe.SceneRecipeError, match="tab_color"):
        recipe.load_scene("bad")


def test_unknown_pane_key_is_rejected(scenes_root: Path) -> None:
    _write(scenes_root, "bad", '[[pane]]\ntile = "typo"\n')
    with pytest.raises(recipe.SceneRecipeError, match="tile"):
        recipe.load_scene("bad")


def test_wrong_type_is_rejected(scenes_root: Path) -> None:
    _write(scenes_root, "bad", 'layout = 123\n[[pane]]\ntitle = "x"\n')
    with pytest.raises(recipe.SceneRecipeError, match="layout"):
        recipe.load_scene("bad")


def test_no_pane_table_is_rejected(scenes_root: Path) -> None:
    _write(scenes_root, "empty", 'tab_title = "x"\n')
    with pytest.raises(recipe.SceneRecipeError, match="at least one"):
        recipe.load_scene("empty")


def test_malformed_toml_is_rejected(scenes_root: Path) -> None:
    _write(scenes_root, "broken", "this is = = not toml\n")
    with pytest.raises(recipe.SceneRecipeError, match="malformed"):
        recipe.load_scene("broken")


# --------------------------------------------------------------------------- #
# load_scene — path traversal + missing
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["../x", "a/b", "..", ""])
def test_path_traversal_names_are_rejected(scenes_root: Path, name: str) -> None:
    with pytest.raises(recipe.SceneRecipeError):
        recipe.load_scene(name)


def test_traversal_does_not_read_outside_dir(scenes_root: Path, tmp_path: Path) -> None:
    # A sibling file the traversal would target must never be read.
    outside = tmp_path / "kitty-setup" / "secret.toml"
    outside.write_text('[[pane]]\ntitle = "leak"\n', encoding="utf-8")
    with pytest.raises(recipe.SceneRecipeError):
        recipe.load_scene("../secret")


def test_unknown_name_lists_available_scenes(scenes_root: Path) -> None:
    _write(scenes_root, "monitoring", '[[pane]]\ntitle = "x"\n')
    _write(scenes_root, "docker", '[[pane]]\ntitle = "y"\n')
    with pytest.raises(recipe.SceneRecipeError) as exc:
        recipe.load_scene("nope")
    msg = str(exc.value)
    assert "docker" in msg and "monitoring" in msg


# --------------------------------------------------------------------------- #
# scenes_dir resolution
# --------------------------------------------------------------------------- #


def test_scenes_dir_honors_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert recipe.scenes_dir() == tmp_path / "xdg" / "kitty-setup" / "scenes"


def test_scenes_dir_falls_back_to_home_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(recipe.Path, "home", classmethod(lambda cls: tmp_path / "home"))
    assert recipe.scenes_dir() == tmp_path / "home" / ".config" / "kitty-setup" / "scenes"


# --------------------------------------------------------------------------- #
# list_scenes + cli_scene_list
# --------------------------------------------------------------------------- #


def test_list_scenes_rich_summary_sorted(scenes_root: Path) -> None:
    _write(
        scenes_root,
        "monitoring",
        'tab_title = "monitoring"\n[[pane]]\ntitle="a"\n[[pane]]\ntitle="b"\n[[pane]]\ntitle="c"\n',
    )
    _write(
        scenes_root, "docker", 'tab_title = "docker"\n[[pane]]\ntitle="a"\n[[pane]]\ntitle="b"\n'
    )
    summaries = recipe.list_scenes()
    assert [s.name for s in summaries] == ["docker", "monitoring"]
    assert summaries[0].pane_count == 2
    assert summaries[1].pane_count == 3
    assert summaries[1].tab_title == "monitoring"


def test_list_scenes_surfaces_malformed_file(scenes_root: Path) -> None:
    _write(scenes_root, "good", '[[pane]]\ntitle="a"\n')
    _write(scenes_root, "broken", "not = = toml\n")
    summaries = {s.name: s for s in recipe.list_scenes()}
    assert summaries["broken"].error is not None
    assert summaries["good"].error is None


def test_cli_scene_list_table_output(scenes_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(
        scenes_root, "docker", 'tab_title = "docker"\n[[pane]]\ntitle="a"\n[[pane]]\ntitle="b"\n'
    )
    rc = recipe.cli_scene_list(argparse.Namespace(names=False))
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == ["NAME", "TAB", "PANES"]  # aligned header
    row = next(line for line in lines if line.startswith("docker"))
    assert row.split() == ["docker", "docker", "2"]


def test_pad_equalizes_display_width_incl_wide_emoji() -> None:
    # A wide emoji counts as 2 cells; padding equalizes *display* width so
    # downstream columns align even when char counts differ.
    assert recipe._display_width("🐳 docker") == recipe._display_width("ab docker")
    assert recipe._display_width(recipe._pad("🐳 docker", 14)) == 14
    assert recipe._display_width(recipe._pad("t", 14)) == 14


def test_scene_name_completer_globs_stems_without_parsing(scenes_root: Path) -> None:
    _write(scenes_root, "docker", '[[pane]]\ntitle="a"\n')
    _write(scenes_root, "dev", '[[pane]]\ntitle="a"\n')
    _write(scenes_root, "broken", "not = = toml\n")  # malformed must not break it
    assert recipe.scene_name_completer(prefix="d") == ["dev", "docker"]
    assert recipe.scene_name_completer(prefix="") == ["broken", "dev", "docker"]


def test_cli_scene_list_names_only(scenes_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(scenes_root, "docker", 'tab_title = "docker"\n[[pane]]\ntitle="a"\n')
    _write(scenes_root, "monitoring", '[[pane]]\ntitle="a"\n')
    rc = recipe.cli_scene_list(argparse.Namespace(names=True))
    assert rc == 0
    assert capsys.readouterr().out.splitlines() == ["docker", "monitoring"]


def test_cli_scene_list_empty_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))  # dir does not exist
    rc = recipe.cli_scene_list(argparse.Namespace(names=False))
    assert rc == 0
    assert "no scenes yet" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# cli_scene_launch — name-mode dispatch + conflicts
# --------------------------------------------------------------------------- #


def _launch_ns(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "name": None,
        "layout": None,
        "tab_title": None,
        "tab_accent": None,
        "panes": [],
        "to": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_name_and_pane_together_is_contradictory(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = launcher.cli_scene_launch(_launch_ns(name="mon", panes=["title=x"]))
    assert rc == 1
    assert "contradictory" in capsys.readouterr().err


def test_neither_name_nor_pane_is_rejected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = launcher.cli_scene_launch(_launch_ns())
    assert rc == 1
    assert "at least one --pane" in capsys.readouterr().err


def test_style_flag_with_named_scene_is_rejected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = launcher.cli_scene_launch(_launch_ns(name="mon", tab_accent="#ff0000"))
    assert rc == 1
    assert "named scene" in capsys.readouterr().err


def test_named_scene_invokes_launch_scene_with_loaded_args(
    scenes_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        scenes_root,
        "mon",
        'layout = "tall"\ntab_title = "T"\n[[pane]]\ntitle = "p1"\ncmd = "echo p1"\n',
    )
    recorded: dict[str, object] = {}

    def _fake_launch_scene(  # type: ignore[no-untyped-def]
        layout, tab_title, tab_accent, panes, *, to=None, default_cwd=None, origin_window=None
    ):
        recorded.update(
            layout=layout,
            tab_title=tab_title,
            tab_accent=tab_accent,
            panes=panes,
            to=to,
            default_cwd=default_cwd,
            origin_window=origin_window,
        )
        return 0

    monkeypatch.setattr(launcher, "launch_scene", _fake_launch_scene)
    rc = launcher.cli_scene_launch(_launch_ns(name="mon"))
    assert rc == 0
    assert recorded["layout"] == "tall"
    assert recorded["tab_title"] == "T"
    assert recorded["panes"] == [Pane(title="p1", cmd="echo p1")]


# --------------------------------------------------------------------------- #
# 02-13 (WR-02, T-2-78) — a NUL in any recipe string is refused by the loader before any kitten
# call. argv cannot carry a NUL, so `subprocess.run` raised an uncaught ValueError at HEAD.
# --------------------------------------------------------------------------- #

_NUL_BODIES = [
    pytest.param('[[pane]]\ncwd = "/tmp/a\\u0000b"\n\n[[pane]]\ntitle = "p1"\n', id="pane_cwd"),
    pytest.param('[[pane]]\ncmd = "echo a\\u0000b"\n\n[[pane]]\ntitle = "p1"\n', id="pane_cmd"),
    pytest.param(
        'tab_title = "t\\u0000"\n\n[[pane]]\ntitle = "p0"\n\n[[pane]]\ntitle = "p1"\n',
        id="tab_title",
    ),
]


@pytest.mark.parametrize("body", _NUL_BODIES)
def test_recipe_nul_refused_before_any_kitten_call(
    scenes_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: str,
) -> None:
    _write(scenes_root, "nul", body)
    monkeypatch.delenv("KITTY_WINDOW_ID", raising=False)
    calls: list[tuple[str, ...]] = []

    def _recorder(verb: str, *args: str, to: str | None = None) -> subprocess.CompletedProcess[str]:
        calls.append((verb, *args))
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="201\n", stderr="")

    monkeypatch.setattr("kitty_setup.scenes._client.kitten_at", _recorder)
    rc = launcher.cli_scene_launch(_launch_ns(name="nul"))
    lines = capsys.readouterr().err.splitlines()
    assert rc == 1
    assert calls == [], f"no kitten call may run for a refused recipe: {calls}"
    assert len(lines) == 1 and lines[0].startswith("my-kitty scene launch: ") and "NUL" in lines[0]
