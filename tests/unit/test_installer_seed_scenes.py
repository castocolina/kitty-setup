"""Unit tests for `installer.seed_scenes` (phase2-scene-polish #3).

Copy-if-absent seeding of example recipes into the user scenes dir, and the
guarantee that the config uninstall never touches that (user-data) directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kitty_setup import config_updater, installer


def _src(tmp_path: Path) -> Path:
    src = tmp_path / "bundled"
    src.mkdir()
    (src / "a.toml").write_text("layout='tall'\n", encoding="utf-8")
    (src / "b.toml").write_text("layout='grid'\n", encoding="utf-8")
    return src


def test_seed_scenes_fresh_copies_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = _src(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr(installer, "_scenes_source", lambda: src)

    seeded, kept = installer.seed_scenes()

    target = tmp_path / "cfg" / "kitty-setup" / "scenes"
    assert (seeded, kept) == (2, 0)
    assert (target / "a.toml").exists() and (target / "b.toml").exists()


def test_seed_scenes_never_overwrites_edited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _src(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr(installer, "_scenes_source", lambda: src)
    target = tmp_path / "cfg" / "kitty-setup" / "scenes"
    target.mkdir(parents=True)
    (target / "a.toml").write_text("EDITED BY USER\n", encoding="utf-8")

    seeded, kept = installer.seed_scenes()

    assert (seeded, kept) == (1, 1)  # b added, a kept
    assert (target / "a.toml").read_text(encoding="utf-8") == "EDITED BY USER\n"
    assert (target / "b.toml").exists()


def test_seed_scenes_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = _src(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr(installer, "_scenes_source", lambda: src)

    installer.seed_scenes()
    seeded, kept = installer.seed_scenes()  # second run

    assert (seeded, kept) == (0, 2)


def test_seed_scenes_handles_missing_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr(installer, "_scenes_source", lambda: tmp_path / "does-not-exist")

    assert installer.seed_scenes() == (0, 0)


def test_uninstall_config_only_leaves_scenes_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Create a user scene, then run the config uninstall and assert it survives —
    # the scenes dir is user data, disjoint from the managed config payload.
    from kitty_setup.scenes.recipe import scenes_dir

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    scenes = scenes_dir()
    scenes.mkdir(parents=True)
    (scenes / "docker.toml").write_text("layout='tall'\n", encoding="utf-8")

    paths = config_updater.ConfigPaths.for_user(home=tmp_path / "home")
    monkeypatch.setattr(
        config_updater.ConfigPaths, "for_user", classmethod(lambda cls, home=None: paths)
    )
    captured: dict[str, object] = {}

    def fake_uninstall(p: config_updater.ConfigPaths) -> config_updater.UninstallResult:
        captured["payload_dir"] = p.payload_dir
        return config_updater.UninstallResult(
            conf_file=p.conf_file,
            block_removed=True,
            payload_dir_removed=True,
            conf_restored_from=None,
            conf_deleted=False,
        )

    monkeypatch.setattr(config_updater, "uninstall", fake_uninstall)

    installer.uninstall_config_only()

    assert (scenes / "docker.toml").exists(), "user scene must survive uninstall"
    assert "scenes" not in str(captured["payload_dir"])  # config uninstall != scenes dir
