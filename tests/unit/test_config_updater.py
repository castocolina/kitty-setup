"""Unit tests for ``kitty_setup.config_updater``.

No real Kitty binary is invoked — the ``parse_check`` callable is stubbed via a
small fake binary script written into ``tmp_path`` for the cases that need it.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import errno
import os
import shlex
import shutil
import stat
from pathlib import Path
from typing import Any

import pytest

from kitty_setup import config_updater
from kitty_setup.config_updater import (
    INCLUDE_LINE,
    MARKER_BEGIN,
    MARKER_END,
    ConfigPaths,
    ConfigUpdaterError,
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


def _fake_kitty_bin(
    tmp_path: Path,
    *,
    exit_code: int,
    stderr: str = "",
    argv_log: Path | None = None,
    name: str | None = None,
) -> Path:
    """Write a tiny shell script that exits with ``exit_code`` regardless of args.

    ``stderr`` is written to the script's stderr verbatim before it exits (kept in a sidecar
    file and ``cat``-ed, so no byte is re-quoted). ``argv_log`` receives the script's own argv,
    ``$0`` included, NUL-separated, so a case can compare it with the command it was told ran.
    """
    script = tmp_path / (name or f"fake-kitty-{exit_code}")
    lines = ["#!/usr/bin/env bash"]
    if argv_log is not None:
        lines.append(f'printf \'%s\\0\' "$0" "$@" > {shlex.quote(str(argv_log))}')
    if stderr:
        sidecar = script.with_name(script.name + ".stderr")
        sidecar.write_text(stderr, encoding="utf-8")
        lines.append(f"cat {shlex.quote(str(sidecar))} >&2")
    lines.append(f"exit {exit_code}")
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


def _recorded_argv(argv_log: Path) -> list[str]:
    return argv_log.read_bytes().decode("utf-8").split("\0")[:-1]


def parse_check(conf_file: Path, kitty_bin: Path) -> Any:
    """Call ``config_updater.parse_check`` through the module namespace.

    Looked up by name rather than by attribute so these cases add no pyright
    ``reportPrivateUsage`` finding; ``02-10`` renames the function and updates this one string.
    """
    return vars(config_updater)["parse_check"](conf_file, kitty_bin)


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


def test_install_appends_to_existing_user_content(paths: ConfigPaths, payload_source: Path) -> None:
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


def test_no_extraneous_writes_to_xdg_paths(paths: ConfigPaths, payload_source: Path) -> None:
    install(paths, payload_source)
    # Footprint check: only the conf, the payload dir, and any backups.
    entries = sorted(p.name for p in paths.kitty_dir.iterdir())
    expected = {"kitty.conf", paths.payload_dir.name}
    actual = set(entries)
    extras = actual - expected
    assert not extras or all(
        name.startswith("kitty.conf.bak.") for name in extras
    ), f"unexpected extra entries: {extras}"


def test_backup_uses_utc_timestamp_format(paths: ConfigPaths, payload_source: Path) -> None:
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


def test_list_backups_empty_when_dir_missing(tmp_path: Path) -> None:
    conf = tmp_path / "no-such" / "kitty.conf"
    assert config_updater.list_backups(conf) == []


def test_list_backups_empty_when_dir_has_no_backups(tmp_path: Path) -> None:
    conf = tmp_path / "kitty.conf"
    conf.write_text("# user\n")
    (tmp_path / "notes.md").write_text("# notes\n")
    assert config_updater.list_backups(conf) == []


def test_list_backups_returns_only_strict_pattern(tmp_path: Path) -> None:
    conf = tmp_path / "kitty.conf"
    conf.write_text("# user\n")
    good_a = tmp_path / "kitty.conf.bak.20260101T000000Z"
    good_b = tmp_path / "kitty.conf.bak.20260102T120000Z"
    bad_1 = tmp_path / "kitty.conf.bak.notadate"
    bad_2 = tmp_path / "kitty.conf.bak.2026-01-01T00:00:00Z"
    bad_3 = tmp_path / "kitty.conf.backup"
    for f in (good_a, good_b, bad_1, bad_2, bad_3):
        f.write_text("backup")
    result = config_updater.list_backups(conf)
    assert result == [good_a, good_b]


def test_list_backups_sort_order_is_lexicographic(tmp_path: Path) -> None:
    conf = tmp_path / "kitty.conf"
    conf.write_text("# user\n")
    names = [
        "kitty.conf.bak.20260101T120000Z",
        "kitty.conf.bak.20260101T000000Z",
        "kitty.conf.bak.20260102T080000Z",
        "kitty.conf.bak.20251231T235959Z",
    ]
    for n in names:
        (tmp_path / n).write_text("x")
    result = [p.name for p in config_updater.list_backups(conf)]
    assert result == sorted(names)


def test_latest_backup_uses_list_backups(tmp_path: Path) -> None:
    conf = tmp_path / "kitty.conf"
    conf.write_text("# user\n")
    (tmp_path / "kitty.conf.bak.20260101T000000Z").write_text("a")
    newest = tmp_path / "kitty.conf.bak.20260102T000000Z"
    newest.write_text("b")
    assert config_updater._latest_backup(conf) == newest


# --- R1.5 (D-09): the parse check returns its diagnostics --------------------------------------
# ``ParseCheckResult`` is reached as a module attribute inside each body, so at RED a missing name
# fails its own case instead of erroring the module at collection.

BAD_LINE_DIAG = (
    "BadLine(number=1, line='cursor_shape banana', exception=ValueError('Invalid cursor shape: "
    "banana allowed values are block, beam, underline'), file='kitty-setup/kitty-setup.conf')\n"
)
MISSING_INCLUDE_WARNING = (
    "[0.009] Could not find included config file: /x/kitty-setup/kitty-setup.conf, ignoring\n"
)


def _conf(tmp_path: Path) -> Path:
    conf = tmp_path / "check" / "kitty.conf"
    conf.parent.mkdir()
    conf.write_text("font_size 12\n", encoding="utf-8")
    return conf


def test_parse_result_carries_ok_command_and_stderr_fields(tmp_path: Path) -> None:
    result = parse_check(_conf(tmp_path), _fake_kitty_bin(tmp_path, exit_code=0))
    # Before the type assertion, which would narrow ``result`` and make this a type error.
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.ok = False
    assert type(result) is config_updater.ParseCheckResult
    assert [f.name for f in dataclasses.fields(result)] == ["ok", "command", "stderr"]


def test_parse_result_command_names_runpy_not_debug_config(tmp_path: Path) -> None:
    result = parse_check(_conf(tmp_path), _fake_kitty_bin(tmp_path, exit_code=0))
    assert "+runpy" in result.command
    assert "--debug-config" not in result.command


def test_parse_result_failure_carries_parser_stderr_verbatim(tmp_path: Path) -> None:
    failing = _fake_kitty_bin(tmp_path, exit_code=1, stderr=BAD_LINE_DIAG)
    result = parse_check(_conf(tmp_path), failing)
    assert result.ok is False
    assert result.stderr == BAD_LINE_DIAG


def test_parse_result_success_passes_stderr_through(tmp_path: Path) -> None:
    conf = _conf(tmp_path)
    silent = parse_check(conf, _fake_kitty_bin(tmp_path, exit_code=0, name="silent"))
    assert silent.ok is True
    assert silent.stderr == ""
    warned = _fake_kitty_bin(tmp_path, exit_code=0, stderr=MISSING_INCLUDE_WARNING, name="warned")
    result = parse_check(conf, warned)
    assert result.ok is True
    assert result.stderr == MISSING_INCLUDE_WARNING


def test_parse_result_command_is_the_complete_argv_executed(tmp_path: Path) -> None:
    argv_log = tmp_path / "argv.bin"
    kitty = _fake_kitty_bin(tmp_path, exit_code=0, argv_log=argv_log)
    conf = _conf(tmp_path)
    result = parse_check(conf, kitty)
    recorded = _recorded_argv(argv_log)
    assert recorded[0] == str(kitty)
    assert recorded[1] == "+runpy"
    assert recorded[-1] == str(conf)
    assert shlex.split(result.command) == recorded


def test_install_parse_result_error_carries_command_and_stderr(
    paths: ConfigPaths, payload_source: Path, tmp_path: Path
) -> None:
    paths.kitty_dir.mkdir(parents=True)
    paths.conf_file.write_text("font_size 12\n", encoding="utf-8")
    argv_log = tmp_path / "argv.bin"
    failing = _fake_kitty_bin(tmp_path, exit_code=1, stderr=BAD_LINE_DIAG, argv_log=argv_log)

    with pytest.raises(ConfigUpdaterError) as exc_info:
        install(paths, payload_source, kitty_bin=failing)

    message = str(exc_info.value)
    assert shlex.join(_recorded_argv(argv_log)) in message
    assert BAD_LINE_DIAG.rstrip() in message
    assert "--debug-config" not in message


# --- R1.5 (D-09): the payload directory rolls back too -----------------------------------------
# "Restored" means the previous bytes are back, not merely that a directory exists. The conf is
# drifted (no block) wherever the parse check must run, so the install mutates it.

NOW = dt.datetime(2026, 9, 24, 12, 0, 0, tzinfo=dt.UTC)
PREVIOUS_MARKER = b"# previous payload marker - must survive a failed install\n"
STALE_MARKER = b"# stale aside from an interrupted install\n"


def _aside(paths: ConfigPaths) -> Path:
    return paths.payload_dir.with_name(paths.payload_dir.name + ".rollback")


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


def _seed_previous_install(paths: ConfigPaths) -> dict[str, bytes]:
    paths.payload_dir.mkdir(parents=True)
    (paths.payload_dir / "kitty-setup.conf").write_bytes(b"# previous payload\n")
    (paths.payload_dir / "previous-marker.conf").write_bytes(PREVIOUS_MARKER)
    paths.conf_file.write_text("font_size 12\n", encoding="utf-8")
    return _snapshot(paths.payload_dir)


def _entries(paths: ConfigPaths) -> list[str]:
    return sorted(p.name for p in paths.kitty_dir.iterdir())


@pytest.mark.parametrize(
    "injected",
    [
        pytest.param(OSError(errno.ENOSPC, "injected: no space left mid-copy"), id="oserror"),
        pytest.param(KeyboardInterrupt(), id="ctrl_c"),
    ],
)
def test_rollback_copy_fails_restores_previous_payload(
    paths: ConfigPaths,
    payload_source: Path,
    monkeypatch: pytest.MonkeyPatch,
    injected: BaseException,
) -> None:
    previous = _seed_previous_install(paths)

    def partial_copy_then_fail(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
        del src, args, kwargs
        Path(dst).mkdir()
        (Path(dst) / "partial.conf").write_text("# half-copied\n", encoding="utf-8")
        raise injected

    monkeypatch.setattr(config_updater.shutil, "copytree", partial_copy_then_fail)

    # A KeyboardInterrupt is raised only inside pytest.raises: one that escaped a case would abort
    # the whole session instead of failing this item.
    with pytest.raises(type(injected)):
        install(paths, payload_source, now=NOW)

    assert _snapshot(paths.payload_dir) == previous
    assert not _aside(paths).exists()
    assert _entries(paths) == ["kitty-setup", "kitty.conf"]
    assert _read(paths.conf_file) == "font_size 12\n"


def test_rollback_parse_fails_restores_previous_payload(
    paths: ConfigPaths, payload_source: Path, tmp_path: Path
) -> None:
    previous = _seed_previous_install(paths)
    failing = _fake_kitty_bin(tmp_path, exit_code=1, stderr=BAD_LINE_DIAG)

    with pytest.raises(ConfigUpdaterError):
        install(paths, payload_source, kitty_bin=failing, now=NOW)

    assert _snapshot(paths.payload_dir) == previous
    assert b"# fake payload\n" not in _snapshot(paths.payload_dir).values()
    assert not _aside(paths).exists()
    assert _read(paths.conf_file) == "font_size 12\n"
    # The backup made before the conf mutation is left on disk (Hidden Coupling #8).
    backup = f"kitty.conf.bak.{NOW.strftime(config_updater.BACKUP_SUFFIX_FMT)}"
    assert _entries(paths) == ["kitty-setup", "kitty.conf", backup]


@pytest.mark.parametrize("failing_step", ["rename_back", "remove_target"])
def test_rollback_restore_fails_keeps_and_names_the_aside(
    paths: ConfigPaths,
    payload_source: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_step: str,
) -> None:
    previous = _seed_previous_install(paths)
    conf_before = paths.conf_file.read_bytes()
    aside = _aside(paths)
    failing = _fake_kitty_bin(tmp_path, exit_code=1, stderr=BAD_LINE_DIAG)
    injected = OSError(errno.EIO, f"injected {failing_step} failure")

    if failing_step == "rename_back":
        real_rename = Path.rename

        def rename(self: Path, target: Any) -> Path:
            if self == aside:
                raise injected
            return real_rename(self, target)

        monkeypatch.setattr(Path, "rename", rename)
    else:
        real_rmtree = shutil.rmtree

        def rmtree(path: Any, ignore_errors: bool = False) -> None:
            if Path(path) == paths.payload_dir:
                raise injected
            real_rmtree(path, ignore_errors=ignore_errors)

        monkeypatch.setattr(config_updater.shutil, "rmtree", rmtree)

    with pytest.raises(ConfigUpdaterError) as exc_info:
        install(paths, payload_source, kitty_bin=failing, now=NOW)

    message = str(exc_info.value)
    assert exc_info.value.__cause__ is injected
    assert str(aside) in message
    assert BAD_LINE_DIAG.rstrip() in message
    assert _snapshot(aside) == previous
    assert paths.conf_file.read_bytes() == conf_before


def test_rollback_no_previous_payload_leaves_no_payload_dir(
    paths: ConfigPaths, payload_source: Path, tmp_path: Path
) -> None:
    paths.kitty_dir.mkdir(parents=True)
    paths.conf_file.write_text("font_size 12\n", encoding="utf-8")
    failing = _fake_kitty_bin(tmp_path, exit_code=1, stderr=BAD_LINE_DIAG)

    with pytest.raises(ConfigUpdaterError):
        install(paths, payload_source, kitty_bin=failing, now=NOW)

    assert not paths.payload_dir.exists()
    assert not _aside(paths).exists()
    assert _read(paths.conf_file) == "font_size 12\n"


def _seed_stale_aside(paths: ConfigPaths) -> Path:
    stale = _aside(paths)
    stale.mkdir()
    (stale / "stale-marker.conf").write_bytes(STALE_MARKER)
    return stale


def test_rollback_stale_aside_preserved_under_a_dated_name(
    paths: ConfigPaths,
    payload_source: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_previous_install(paths)
    stale = _seed_stale_aside(paths)
    passing = _fake_kitty_bin(tmp_path, exit_code=0)
    preserved = stale.with_name(stale.name + "." + NOW.strftime(config_updater.BACKUP_SUFFIX_FMT))

    install(paths, payload_source, kitty_bin=passing, now=NOW)

    assert (preserved / "stale-marker.conf").read_bytes() == STALE_MARKER
    assert _snapshot(paths.payload_dir) == _snapshot(payload_source)
    assert not stale.exists()
    err_lines = capsys.readouterr().err.splitlines()
    assert len(err_lines) == 1
    assert str(preserved) in err_lines[0]


def test_rollback_stale_aside_preserved_under_the_smallest_free_suffix(
    paths: ConfigPaths,
    payload_source: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A taken name means "exists": renaming onto an *empty* directory silently replaces it."""
    _seed_previous_install(paths)
    stale = _seed_stale_aside(paths)
    dated = stale.with_name(stale.name + "." + NOW.strftime(config_updater.BACKUP_SUFFIX_FMT))
    dated.mkdir()  # empty: the case a bare rename would silently overwrite
    taken_1 = dated.with_name(dated.name + ".1")
    taken_1.write_bytes(b"not ours to overwrite\n")
    preserved = dated.with_name(dated.name + ".2")
    passing = _fake_kitty_bin(tmp_path, exit_code=0)

    install(paths, payload_source, kitty_bin=passing, now=NOW)

    assert (preserved / "stale-marker.conf").read_bytes() == STALE_MARKER
    assert dated.is_dir()
    assert not any(dated.iterdir())
    assert taken_1.read_bytes() == b"not ours to overwrite\n"
    assert not stale.exists()
    err_lines = capsys.readouterr().err.splitlines()
    assert len(err_lines) == 1
    assert str(preserved) in err_lines[0]


def test_guard_success_leaves_no_aside(
    paths: ConfigPaths, payload_source: Path, tmp_path: Path
) -> None:
    _seed_previous_install(paths)
    passing = _fake_kitty_bin(tmp_path, exit_code=0)

    result = install(paths, payload_source, kitty_bin=passing, now=NOW)

    assert result.parse_ok is True
    assert _snapshot(paths.payload_dir) == _snapshot(payload_source)
    assert not _aside(paths).exists()
    assert not [name for name in _entries(paths) if ".rollback" in name]
