"""Unit tests for the shell-completion file the installer generates and owns (R1.1, D-01..D-03).

The completion script is generated in-process by ``argcomplete.shellcode()`` at install time and
written under ``~/.local/share/kitty-setup/``. Its currency is provable only by regenerating it and
comparing bytes: the script names no subcommand at all (U-3), so no CLI-surface change can stale it.

Every case reaches the code under test as ``installer.<name>`` inside its body, so a missing API
fails each case on its own rather than failing the whole module at collection. Every case runs
against a ``tmp_path`` home; ``HOME`` is also redirected so nothing can reach the real one.
"""

from __future__ import annotations

import argparse
import errno
import os
import re
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Final

import argcomplete
import pytest

from kitty_setup import config_updater, installer, path_integration, pruner

_SUBCOMMAND_NAMES = ("doctor", "prune", "keys", "scene", "uninstall", "install")

# The reference is argcomplete itself, called in this interpreter — never the installer's own
# generator — so the byte match holds whichever argcomplete version resolves. argcomplete 3.6.3
# defines ``shellcode`` unannotated and outside ``__all__``; the namespace lookup plus annotation
# keeps pyright strict clean without a suppression comment.
_ARGCOMPLETE_SHELLCODE: Final[Callable[..., str]] = vars(argcomplete)["shellcode"]


def _fresh_shellcode(*, shell: str) -> str:
    return _ARGCOMPLETE_SHELLCODE(["my-kitty"], shell=shell)


def _completion_dir(home: Path) -> Path:
    return home / ".local" / "share" / "kitty-setup"


@pytest.fixture(autouse=True)
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``HOME`` at the test's own directory for every case in this module."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _redirect_default_dir(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    """Point the module-level default completion directory at ``home``.

    Called inside each test body — never from a fixture — so that a missing
    ``installer.COMPLETION_DIR`` fails the case rather than erroring its setup.
    """
    monkeypatch.setattr(installer, "COMPLETION_DIR", _completion_dir(home))


# --------------------------------------------------------------------------- generation


def test_write_bash_shellcode_matches_fresh_generation(tmp_path: Path) -> None:
    path = installer.write_completion_script("bash", home=tmp_path)
    assert path is not None
    assert path == _completion_dir(tmp_path) / "my-kitty-completion.bash"
    assert path == installer.completion_script_path("bash", home=tmp_path)
    assert path.read_text(encoding="utf-8") == _fresh_shellcode(shell="bash")


def test_zsh_script_written_as_fpath_function(tmp_path: Path) -> None:
    """The zsh script is ``_my-kitty``: its ``#compdef`` header lets fpath autoload it (02-14)."""
    path = installer.write_completion_script("zsh", home=tmp_path)
    assert path is not None
    assert path == _completion_dir(tmp_path) / "_my-kitty"
    assert path == installer.completion_script_path("zsh", home=tmp_path)
    assert path.read_text(encoding="utf-8") == _fresh_shellcode(shell="zsh")
    assert path.read_text(encoding="utf-8").splitlines()[0] == "#compdef my-kitty"


def test_legacy_zsh_script_removed_on_zsh_write(tmp_path: Path) -> None:
    directory = _completion_dir(tmp_path)
    directory.mkdir(parents=True)
    legacy = directory / "my-kitty-completion.zsh"
    legacy.write_text("legacy\n", encoding="utf-8")
    installer.write_completion_script("zsh", home=tmp_path)
    assert not legacy.exists()
    assert (directory / "_my-kitty").is_file()


def test_legacy_zsh_script_removed_on_uninstall(tmp_path: Path) -> None:
    directory = _completion_dir(tmp_path)
    directory.mkdir(parents=True)
    current = directory / "_my-kitty"
    current.write_text("current\n", encoding="utf-8")
    legacy = directory / "my-kitty-completion.zsh"
    legacy.write_text("legacy\n", encoding="utf-8")
    removed = installer.remove_completion_script(home=tmp_path)
    assert sorted(removed) == sorted([current, legacy])
    assert not legacy.exists()


def test_bash_write_leaves_legacy_zsh_file(tmp_path: Path) -> None:
    """A bash write keeps the 02-02-era zsh file: an untouched ~/.zshrc still sources it."""
    directory = _completion_dir(tmp_path)
    directory.mkdir(parents=True)
    legacy = directory / "my-kitty-completion.zsh"
    legacy.write_bytes(b"legacy zsh bytes\n")
    installer.write_completion_script("bash", home=tmp_path)
    assert legacy.read_bytes() == b"legacy zsh bytes\n"


def test_zsh_script_dir_not_group_or_world_writable(tmp_path: Path) -> None:
    """A zsh write clears group and world write on the directory: zsh's compaudit rule (02-14)."""
    directory = _completion_dir(tmp_path)
    directory.mkdir(parents=True)
    directory.chmod(0o777)
    installer.write_completion_script("zsh", home=tmp_path)
    assert stat.S_IMODE(directory.stat().st_mode) & 0o022 == 0


def test_generate_completion_script_is_the_in_process_shellcode() -> None:
    for shell in ("bash", "zsh"):
        expected = _fresh_shellcode(shell=shell)
        assert installer.generate_completion_script(shell) == expected


def test_generated_script_names_no_subcommand(tmp_path: Path) -> None:
    """Tombstone for U-3: the script dispatches to the program at completion time.

    It names no subcommand, so a test asserting that a CLI-surface change alters
    the file would fail immediately. Currency is a byte match against fresh
    shellcode, never a content inspection.
    """
    for shell in ("bash", "zsh"):
        path = installer.write_completion_script(shell, home=tmp_path)
        assert path is not None
        text = path.read_text(encoding="utf-8")
        for name in _SUBCOMMAND_NAMES:
            assert re.search(rf"\b{name}\b", text) is None, f"{name!r} found in {shell} script"


def test_generated_script_starts_with_compdef_header(tmp_path: Path) -> None:
    """``#compdef my-kitty`` is a zsh header and a bash comment: one generator, two shells."""
    for shell in ("bash", "zsh"):
        path = installer.write_completion_script(shell, home=tmp_path)
        assert path is not None
        assert path.read_text(encoding="utf-8").splitlines()[0] == "#compdef my-kitty"


def test_unsupported_shell_fish_writes_nothing(tmp_path: Path) -> None:
    assert installer.write_completion_script("fish", home=tmp_path) is None
    assert not _completion_dir(tmp_path).exists()
    assert not (tmp_path / ".local").exists()


def test_unsupported_shell_none_writes_nothing(tmp_path: Path) -> None:
    assert installer.write_completion_script(None, home=tmp_path) is None
    assert not _completion_dir(tmp_path).exists()
    assert not (tmp_path / ".local").exists()


def test_write_is_idempotent(tmp_path: Path) -> None:
    first = installer.write_completion_script("bash", home=tmp_path)
    assert first is not None
    first_bytes = first.read_bytes()
    second = installer.write_completion_script("bash", home=tmp_path)
    assert second is not None
    assert second == first
    assert second.read_bytes() == first_bytes
    assert sorted(p.name for p in _completion_dir(tmp_path).iterdir()) == [
        "my-kitty-completion.bash"
    ]


# --------------------------------------------------------------------------- cli_install wiring


def _fake_report() -> installer.InstallReport:
    base = Path("/nonexistent-kitty-setup-test")
    return installer.InstallReport(
        kitty_app_dir=base / "kitty.app",
        symlink=base / "bin" / "kitty",
        desktop_entry=base / "kitty.desktop",
        version="0.0.0",
        skipped_kitty_install=True,
        config_result=config_updater.InstallResult(
            conf_file=base / "kitty.conf",
            payload_dir=base / "kitty-setup",
            backup_path=None,
            created_conf=False,
            updated_block=False,
            parse_ok=True,
        ),
    )


def _patch_install_side_effects(monkeypatch: pytest.MonkeyPatch, detected: str | None) -> None:
    """Stub the kitty install and the rc edit so ``cli_install`` touches nothing real."""

    def fake_install(
        *, dest: Path = installer.DEFAULT_DEST, inject_config: bool = True
    ) -> installer.InstallReport:
        return _fake_report()

    def fake_ensure(
        home: Path | None = None, shell: str | None = None
    ) -> path_integration.PathEditResult:
        return path_integration.PathEditResult(
            changed=False,
            skipped=detected not in ("bash", "zsh"),
            rc_file=None,
            shell=detected,
            reason="stubbed",
        )

    monkeypatch.setattr(installer, "install", fake_install)
    monkeypatch.setattr(path_integration, "ensure_local_bin_in_path", fake_ensure)


def test_cli_install_writes_zsh_script_for_detected_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _redirect_default_dir(monkeypatch, tmp_path)
    _patch_install_side_effects(monkeypatch, "zsh")
    rc = installer.cli_install(argparse.Namespace(dest=installer.DEFAULT_DEST, no_config=False))
    assert rc == 0
    written = _completion_dir(tmp_path) / "_my-kitty"
    assert written.read_text(encoding="utf-8") == _fresh_shellcode(shell="zsh")
    assert not (_completion_dir(tmp_path) / "my-kitty-completion.bash").exists()
    assert str(written) in capsys.readouterr().out


def test_cli_install_unsupported_shell_reports_skip_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _redirect_default_dir(monkeypatch, tmp_path)
    _patch_install_side_effects(monkeypatch, "fish")
    rc = installer.cli_install(argparse.Namespace(dest=installer.DEFAULT_DEST, no_config=False))
    assert rc == 0
    assert not _completion_dir(tmp_path).exists()
    completion_lines = [
        line for line in capsys.readouterr().out.splitlines() if line.startswith("completion:")
    ]
    assert len(completion_lines) == 1
    assert "fish" in completion_lines[0]
    assert "source" not in completion_lines[0]


def test_cli_install_completion_write_failure_is_one_clean_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """E1 (D-13): an unwritable completion directory is one stderr line and exit 1.

    ``~/.local`` is made a regular file, so the real ``mkdir`` inside the write raises
    ``NotADirectoryError`` — a genuine OS failure, with nothing stubbed in the unit under test.
    """
    _redirect_default_dir(monkeypatch, tmp_path)
    _patch_install_side_effects(monkeypatch, "bash")
    (tmp_path / ".local").write_text("not a directory\n", encoding="utf-8")
    rc = installer.cli_install(argparse.Namespace(dest=installer.DEFAULT_DEST, no_config=False))
    captured = capsys.readouterr()
    assert rc == 1
    err_lines = [line for line in captured.err.splitlines() if line.strip()]
    assert len(err_lines) == 1, captured.err
    assert str(_completion_dir(tmp_path)) in err_lines[0]
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err


def test_cli_install_path_rc_oserror_is_one_clean_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """R1.7: an ``OSError`` from the rc edit is one stderr line and exit 1, not a traceback.

    Only ``install()`` is stubbed; the rc edit is real. ``~/.zshrc`` is made a directory, so
    the real write inside ``ensure_local_bin_in_path()`` raises ``IsADirectoryError``. Nothing
    after the failed edit runs, so no completion script is written.
    """
    _redirect_default_dir(monkeypatch, tmp_path)

    def fake_install(
        *, dest: Path = installer.DEFAULT_DEST, inject_config: bool = True
    ) -> installer.InstallReport:
        return _fake_report()

    monkeypatch.setattr(installer, "install", fake_install)
    monkeypatch.setenv("SHELL", "/bin/zsh")
    rc_file = tmp_path / ".zshrc"
    rc_file.mkdir()
    rc = installer.cli_install(argparse.Namespace(dest=installer.DEFAULT_DEST, no_config=False))
    captured = capsys.readouterr()
    assert rc == 1
    err_lines = [line for line in captured.err.splitlines() if line.strip()]
    assert len(err_lines) == 1, captured.err
    assert str(rc_file) in err_lines[0]
    assert os.strerror(errno.EISDIR) in err_lines[0]
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
    assert not _completion_dir(tmp_path).exists()
    assert rc_file.is_dir() and not any(rc_file.iterdir())


# --------------------------------------------------------------------------- removal


def test_remove_completion_script_deletes_both_and_prunes_empty_dir(tmp_path: Path) -> None:
    bash = installer.write_completion_script("bash", home=tmp_path)
    zsh = installer.write_completion_script("zsh", home=tmp_path)
    assert bash is not None and zsh is not None
    removed = installer.remove_completion_script(home=tmp_path)
    assert sorted(removed) == sorted([bash, zsh])
    assert not _completion_dir(tmp_path).exists()
    assert (tmp_path / ".local" / "share").is_dir()


def test_remove_completion_script_is_a_noop_when_nothing_exists(tmp_path: Path) -> None:
    assert installer.remove_completion_script(home=tmp_path) == []
    assert not _completion_dir(tmp_path).exists()


def test_remove_completion_script_keeps_dir_holding_a_foreign_file(tmp_path: Path) -> None:
    """Never a recursive delete: a file we do not own keeps the directory alive."""
    bash = installer.write_completion_script("bash", home=tmp_path)
    assert bash is not None
    foreign = _completion_dir(tmp_path) / "user-notes.txt"
    foreign.write_text("mine\n", encoding="utf-8")
    assert installer.remove_completion_script(home=tmp_path) == [bash]
    assert foreign.read_text(encoding="utf-8") == "mine\n"


# --------------------------------------------------------------------------- cli_uninstall wiring


def _ns(**flags: bool) -> argparse.Namespace:
    return argparse.Namespace(
        keep_backups=flags.get("keep_backups", False),
        keep_config=flags.get("keep_config", False),
        keep_kitty=flags.get("keep_kitty", False),
    )


@pytest.fixture
def uninstall_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the config, backup and kitty.app removals, as ``test_installer_uninstall`` does.

    Only attributes that already exist are patched here, so the fixture itself
    cannot error; the completion-specific API is reached inside each test body.
    """

    def fake_uninstall(paths: config_updater.ConfigPaths) -> config_updater.UninstallResult:
        return config_updater.UninstallResult(
            conf_file=paths.conf_file,
            block_removed=False,
            payload_dir_removed=False,
            conf_restored_from=None,
            conf_deleted=False,
        )

    def fake_list_backups(conf_file: Path) -> list[Path]:
        return []

    def fake_delete_each(paths: list[Path]) -> int:
        return 0

    def fake_remove_kitty(dest: Path = installer.DEFAULT_DEST) -> installer.KittyRemovalReport:
        return installer.KittyRemovalReport(
            app_dir=dest / installer.KITTY_APP_DIRNAME,
            app_dir_removed=False,
            symlink=installer.SYMLINK_PATH,
            symlink_removed=False,
            desktop_entry=installer.DESKTOP_PATH,
            desktop_entry_removed=False,
        )

    monkeypatch.setattr(config_updater, "uninstall", fake_uninstall)
    monkeypatch.setattr(config_updater, "list_backups", fake_list_backups)
    monkeypatch.setattr(pruner, "delete_each", fake_delete_each)
    monkeypatch.setattr(installer, "remove_kitty_install", fake_remove_kitty)


@pytest.mark.usefixtures("uninstall_stubs")
def test_cli_uninstall_default_removes_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _redirect_default_dir(monkeypatch, tmp_path)
    path = installer.write_completion_script("bash", home=tmp_path)
    assert path is not None and path.is_file()
    assert installer.cli_uninstall(_ns()) == 0
    assert not path.exists()


@pytest.mark.usefixtures("uninstall_stubs")
def test_cli_uninstall_keep_kitty_preserves_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``make clean`` passes ``--keep-kitty``: a binary that survives keeps its completion."""
    _redirect_default_dir(monkeypatch, tmp_path)
    path = installer.write_completion_script("bash", home=tmp_path)
    assert path is not None and path.is_file()
    assert installer.cli_uninstall(_ns(keep_kitty=True)) == 0
    assert path.read_text(encoding="utf-8") == _fresh_shellcode(shell="bash")


@pytest.mark.usefixtures("uninstall_stubs")
def test_cli_uninstall_keep_config_still_removes_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The file belongs to the binary, not to the ``~/.config/kitty`` footprint."""
    _redirect_default_dir(monkeypatch, tmp_path)
    path = installer.write_completion_script("zsh", home=tmp_path)
    assert path is not None and path.is_file()
    assert installer.cli_uninstall(_ns(keep_config=True)) == 0
    assert not path.exists()
