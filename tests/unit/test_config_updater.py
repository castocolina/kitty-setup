"""Unit tests for ``kitty_setup.config_updater``.

No real Kitty binary is invoked — the ``parse_check`` callable is stubbed via a
small fake binary script written into ``tmp_path`` for the cases that need it.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from kitty_setup import config_updater
from kitty_setup.config_updater import (
    ConfigPaths,
    ConfigUpdaterError,
    INCLUDE_LINE,
    MARKER_BEGIN,
    MARKER_END,
    install,
    is_block_present,
    uninstall,
)


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    h.mkdir()
    return h


@pytest.fixture()
def paths(home: Path) -> ConfigPaths:
    return ConfigPaths.for_user(home=home)


@pytest.fixture()
def payload_source(tmp_path: Path) -> Path:
    src = tmp_path / "payload"
    src.mkdir()
    (src / "kitty-setup.conf").write_text("# fake payload\n", encoding="utf-8")
    return src


def _fake_kitty_bin(tmp_path: Path, *, exit_code: int) -> Path:
    """Write a tiny shell script that exits with ``exit_code`` regardless of args."""
    script = tmp_path / f"fake-kitty-{exit_code}"
    script.write_text(
        f"#!/usr/bin/env bash\nexit {exit_code}\n", encoding="utf-8"
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_install_creates_conf_when_missing(paths: ConfigPaths, payload_source: Path) -> None:
    result = install(paths, payload_source)
    assert result.created_conf
    assert not result.updated_block
    assert result.backup_path is None
    assert result.parse_ok is None
    content = _read(paths.conf_file)
    assert MARKER_BEGIN in content
    assert INCLUDE_LINE in content
    assert MARKER_END in content
    assert (paths.payload_dir / "kitty-setup.conf").is_file()


def test_install_appends_to_existing_user_content(
    paths: ConfigPaths, payload_source: Path
) -> None:
    paths.kitty_dir.mkdir(parents=True)
    paths.conf_file.write_text("font_size 12\nbackground #000\n", encoding="utf-8")

    result = install(paths, payload_source)

    assert not result.created_conf
    assert result.updated_block
    assert result.backup_path is not None
    assert result.backup_path.is_file()
    assert _read(result.backup_path) == "font_size 12\nbackground #000\n"

    content = _read(paths.conf_file)
    assert content.startswith("font_size 12\nbackground #000\n")
    assert content.rstrip().endswith(MARKER_END)


def test_install_is_idempotent_when_block_already_correct(
    paths: ConfigPaths, payload_source: Path
) -> None:
    install(paths, payload_source)
    backups_before = sorted(paths.kitty_dir.glob("kitty.conf.bak.*"))
    snapshot = _read(paths.conf_file)

    second = install(paths, payload_source)

    assert not second.updated_block
    assert not second.created_conf
    assert second.backup_path is None
    assert _read(paths.conf_file) == snapshot
    assert sorted(paths.kitty_dir.glob("kitty.conf.bak.*")) == backups_before


def test_install_replaces_drifted_block(paths: ConfigPaths, payload_source: Path) -> None:
    paths.kitty_dir.mkdir(parents=True)
    paths.conf_file.write_text(
        "\n".join(
            [
                "user_line a",
                MARKER_BEGIN,
                "include some-other-thing.conf",
                MARKER_END,
                "user_line b",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = install(paths, payload_source)

    assert result.updated_block
    assert result.backup_path is not None
    content = _read(paths.conf_file)
    assert "include some-other-thing.conf" not in content
    assert INCLUDE_LINE in content
    assert "user_line a" in content
    assert "user_line b" in content


def test_install_parse_check_failure_rolls_back(
    paths: ConfigPaths, payload_source: Path, tmp_path: Path
) -> None:
    paths.kitty_dir.mkdir(parents=True)
    paths.conf_file.write_text("font_size 12\n", encoding="utf-8")
    failing_kitty = _fake_kitty_bin(tmp_path, exit_code=1)

    with pytest.raises(ConfigUpdaterError):
        install(paths, payload_source, kitty_bin=failing_kitty)

    # File restored from backup; backup itself preserved.
    assert _read(paths.conf_file) == "font_size 12\n"
    backups = sorted(paths.kitty_dir.glob("kitty.conf.bak.*"))
    assert len(backups) == 1


def test_install_parse_check_failure_deletes_created_conf(
    paths: ConfigPaths, payload_source: Path, tmp_path: Path
) -> None:
    failing_kitty = _fake_kitty_bin(tmp_path, exit_code=1)

    with pytest.raises(ConfigUpdaterError):
        install(paths, payload_source, kitty_bin=failing_kitty)

    assert not paths.conf_file.exists()


def test_install_parse_check_success_records_parse_ok(
    paths: ConfigPaths, payload_source: Path, tmp_path: Path
) -> None:
    passing_kitty = _fake_kitty_bin(tmp_path, exit_code=0)
    result = install(paths, payload_source, kitty_bin=passing_kitty)
    assert result.parse_ok is True


def test_uninstall_strips_block_and_keeps_user_content(
    paths: ConfigPaths, payload_source: Path
) -> None:
    paths.kitty_dir.mkdir(parents=True)
    paths.conf_file.write_text("font_size 12\n", encoding="utf-8")
    install(paths, payload_source)

    result = uninstall(paths)

    assert result.block_removed
    assert result.payload_dir_removed
    assert _read(paths.conf_file).rstrip() == "font_size 12"
    assert not paths.payload_dir.exists()
    # Backups stay put.
    assert sorted(paths.kitty_dir.glob("kitty.conf.bak.*"))


def test_uninstall_restores_backup_when_only_our_block_remained(
    paths: ConfigPaths, payload_source: Path
) -> None:
    paths.kitty_dir.mkdir(parents=True)
    # User had a previous file with content; back it up before our block lands.
    paths.conf_file.write_text("font_size 14\n", encoding="utf-8")
    install(paths, payload_source)
    # Nuke the user line so the conf only contains our block + the backup line.
    block_only = "\n".join([MARKER_BEGIN, INCLUDE_LINE, MARKER_END, ""])
    paths.conf_file.write_text(block_only, encoding="utf-8")

    result = uninstall(paths)

    assert result.block_removed
    assert result.conf_restored_from is not None
    assert _read(paths.conf_file) == "font_size 14\n"


def test_uninstall_deletes_conf_when_no_backup_and_no_user_content(
    paths: ConfigPaths, payload_source: Path
) -> None:
    install(paths, payload_source)  # creates fresh conf with only our block

    result = uninstall(paths)

    assert result.block_removed
    assert result.conf_deleted
    assert not paths.conf_file.exists()


def test_uninstall_when_nothing_present_is_noop(paths: ConfigPaths) -> None:
    result = uninstall(paths)
    assert not result.block_removed
    assert not result.payload_dir_removed
    assert not result.conf_deleted
    assert result.conf_restored_from is None


def test_is_block_present(paths: ConfigPaths, payload_source: Path) -> None:
    assert not is_block_present(paths)
    install(paths, payload_source)
    assert is_block_present(paths)
    uninstall(paths)
    assert not is_block_present(paths)


def test_install_rejects_missing_payload(paths: ConfigPaths, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        install(paths, tmp_path / "does-not-exist")


def test_install_rejects_payload_that_is_a_file(paths: ConfigPaths, tmp_path: Path) -> None:
    not_a_dir = tmp_path / "file"
    not_a_dir.write_text("x", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        install(paths, not_a_dir)


def test_repeated_install_overwrites_payload(
    paths: ConfigPaths, payload_source: Path, tmp_path: Path
) -> None:
    install(paths, payload_source)
    # Second payload with a different file set; install should mirror it.
    other = tmp_path / "payload2"
    other.mkdir()
    (other / "kitty-setup.conf").write_text("# v2\n", encoding="utf-8")
    (other / "extra.conf").write_text("# extra\n", encoding="utf-8")

    install(paths, other)

    assert _read(paths.payload_dir / "kitty-setup.conf") == "# v2\n"
    assert (paths.payload_dir / "extra.conf").is_file()


def test_no_extraneous_writes_to_xdg_paths(
    paths: ConfigPaths, payload_source: Path
) -> None:
    install(paths, payload_source)
    # Footprint check: only the conf, the payload dir, and any backups.
    entries = sorted(p.name for p in paths.kitty_dir.iterdir())
    expected = {"kitty.conf", paths.payload_dir.name}
    actual = set(entries)
    extras = actual - expected
    assert not extras or all(name.startswith("kitty.conf.bak.") for name in extras), (
        f"unexpected extra entries: {extras}"
    )


def test_backup_uses_utc_timestamp_format(
    paths: ConfigPaths, payload_source: Path
) -> None:
    paths.kitty_dir.mkdir(parents=True)
    paths.conf_file.write_text("x\n", encoding="utf-8")
    result = install(paths, payload_source)
    assert result.backup_path is not None
    suffix = result.backup_path.name.removeprefix("kitty.conf.bak.")
    # YYYYMMDDTHHMMSSZ — 16 chars total
    assert len(suffix) == 16
    assert suffix.endswith("Z")
    assert suffix[8] == "T"


def test_block_only_file_with_trailing_user_content_is_kept(
    paths: ConfigPaths, payload_source: Path
) -> None:
    install(paths, payload_source)
    # Append user content after our block, then uninstall.
    with paths.conf_file.open("a", encoding="utf-8") as fh:
        fh.write("trailing_user_line yes\n")

    result = uninstall(paths)

    assert result.block_removed
    assert result.conf_restored_from is None  # had real user content, no restore
    assert _read(paths.conf_file).rstrip() == "trailing_user_line yes"


def test_install_does_not_touch_files_outside_kitty_dir(
    paths: ConfigPaths, payload_source: Path, home: Path
) -> None:
    sentinel = home / "untouched.txt"
    sentinel.write_text("safe\n", encoding="utf-8")
    install(paths, payload_source)
    assert _read(sentinel) == "safe\n"


def test_parse_check_with_missing_kitty_binary_raises(
    paths: ConfigPaths, payload_source: Path, tmp_path: Path
) -> None:
    paths.kitty_dir.mkdir(parents=True)
    paths.conf_file.write_text("font_size 12\n", encoding="utf-8")
    missing = tmp_path / "no-such-kitty"
    with pytest.raises(ConfigUpdaterError):
        install(paths, payload_source, kitty_bin=missing)


def test_block_text_constant_shape() -> None:
    # Cheap regression guard against accidental marker drift.
    text = config_updater._block_text()
    assert text == f"{MARKER_BEGIN}\n{INCLUDE_LINE}\n{MARKER_END}\n"


def test_environment_variable_does_not_affect_paths(
    monkeypatch: pytest.MonkeyPatch, home: Path
) -> None:
    # Sanity: ConfigPaths.for_user(home=...) ignores env-derived overrides.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "elsewhere"))
    paths = ConfigPaths.for_user(home=home)
    assert paths.kitty_dir == home / ".config" / "kitty"
    assert os.environ["XDG_CONFIG_HOME"] == str(home / "elsewhere")
