"""Unit tests for ``installer.cli_uninstall`` flag combinations.

Default scope removes everything; ``--keep-*`` flags preserve subsets.
Each test monkeypatches the four real-side-effect helpers
(``uninstall_config_only``, ``config_updater.list_backups``,
``pruner.delete_each``, ``remove_kitty_install``) and asserts which were
invoked. The self-removal banner ALWAYS prints.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from kitty_setup import config_updater, installer, pruner


def _ns(**flags: bool) -> argparse.Namespace:
    return argparse.Namespace(
        keep_backups=flags.get("keep_backups", False),
        keep_config=flags.get("keep_config", False),
        keep_kitty=flags.get("keep_kitty", False),
    )


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[object]]:
    """Patch all four side-effect helpers; record invocations."""
    record: dict[str, list[object]] = {
        "uninstall": [],
        "list_backups": [],
        "delete_each": [],
        "remove_kitty": [],
    }
    fake_backups = [Path("/tmp/kitty.conf.bak.20260101T000000Z")]

    def fake_uninstall(paths: config_updater.ConfigPaths) -> config_updater.UninstallResult:
        record["uninstall"].append(paths)
        return config_updater.UninstallResult(
            conf_file=paths.conf_file,
            block_removed=True,
            payload_dir_removed=True,
            conf_restored_from=None,
            conf_deleted=False,
        )

    def fake_list_backups(conf_file: Path) -> list[Path]:
        record["list_backups"].append(conf_file)
        return list(fake_backups)

    def fake_delete_each(paths: object) -> int:
        items = list(paths)  # type: ignore[arg-type]
        record["delete_each"].append(items)
        return len(items)

    def fake_remove_kitty(dest: Path = installer.DEFAULT_DEST) -> installer.KittyRemovalReport:
        record["remove_kitty"].append(dest)
        return installer.KittyRemovalReport(
            app_dir=dest / installer.KITTY_APP_DIRNAME,
            app_dir_removed=True,
            symlink=installer.SYMLINK_PATH,
            symlink_removed=True,
            desktop_entry=installer.DESKTOP_PATH,
            desktop_entry_removed=True,
        )

    monkeypatch.setattr(config_updater, "uninstall", fake_uninstall)
    monkeypatch.setattr(config_updater, "list_backups", fake_list_backups)
    monkeypatch.setattr(pruner, "delete_each", fake_delete_each)
    monkeypatch.setattr(installer, "remove_kitty_install", fake_remove_kitty)
    return record


def test_default_no_flags_invokes_all_three(
    calls: dict[str, list[object]], capsys: pytest.CaptureFixture[str]
) -> None:
    rc = installer.cli_uninstall(_ns())
    assert rc == 0
    assert len(calls["list_backups"]) == 1
    assert len(calls["delete_each"]) == 1
    assert len(calls["uninstall"]) == 1
    assert len(calls["remove_kitty"]) == 1
    out = capsys.readouterr().out
    assert "uv tool uninstall my-kitty" in out


def test_keep_backups_skips_backup_deletion_only(calls: dict[str, list[object]]) -> None:
    installer.cli_uninstall(_ns(keep_backups=True))
    assert calls["list_backups"] == []
    assert calls["delete_each"] == []
    assert len(calls["uninstall"]) == 1
    assert len(calls["remove_kitty"]) == 1


def test_keep_config_skips_config_and_backups(calls: dict[str, list[object]]) -> None:
    installer.cli_uninstall(_ns(keep_config=True))
    assert calls["list_backups"] == []
    assert calls["delete_each"] == []
    assert calls["uninstall"] == []
    assert len(calls["remove_kitty"]) == 1


def test_keep_kitty_skips_kitty_only(calls: dict[str, list[object]]) -> None:
    installer.cli_uninstall(_ns(keep_kitty=True))
    assert len(calls["list_backups"]) == 1
    assert len(calls["delete_each"]) == 1
    assert len(calls["uninstall"]) == 1
    assert calls["remove_kitty"] == []


def test_keep_backups_and_kitty_compose(calls: dict[str, list[object]]) -> None:
    installer.cli_uninstall(_ns(keep_backups=True, keep_kitty=True))
    assert calls["list_backups"] == []
    assert calls["delete_each"] == []
    assert len(calls["uninstall"]) == 1
    assert calls["remove_kitty"] == []


def test_all_three_keep_flags_reduce_to_banner_only(
    calls: dict[str, list[object]], capsys: pytest.CaptureFixture[str]
) -> None:
    rc = installer.cli_uninstall(_ns(keep_backups=True, keep_config=True, keep_kitty=True))
    assert rc == 0
    assert calls["list_backups"] == []
    assert calls["delete_each"] == []
    assert calls["uninstall"] == []
    assert calls["remove_kitty"] == []
    out = capsys.readouterr().out
    assert "uv tool uninstall my-kitty" in out


def test_self_removal_banner_prints_regardless_of_flags(
    calls: dict[str, list[object]], capsys: pytest.CaptureFixture[str]
) -> None:
    installer.cli_uninstall(_ns(keep_kitty=True))
    out = capsys.readouterr().out
    assert "uv tool uninstall my-kitty" in out
    assert "# >>> my-kitty PATH >>>" in out


def test_no_backups_present_prints_nothing_to_delete(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Empty backup list → 'nothing to delete' rather than 'deleted 0'."""

    def fake_list_backups(_: Path) -> list[Path]:
        return []

    monkeypatch.setattr(config_updater, "list_backups", fake_list_backups)
    monkeypatch.setattr(pruner, "delete_each", lambda _paths: 0)
    monkeypatch.setattr(
        config_updater,
        "uninstall",
        lambda paths: config_updater.UninstallResult(
            conf_file=paths.conf_file,
            block_removed=False,
            payload_dir_removed=False,
            conf_restored_from=None,
            conf_deleted=False,
        ),
    )
    monkeypatch.setattr(
        installer,
        "remove_kitty_install",
        lambda dest=installer.DEFAULT_DEST: installer.KittyRemovalReport(
            app_dir=dest / installer.KITTY_APP_DIRNAME,
            app_dir_removed=False,
            symlink=installer.SYMLINK_PATH,
            symlink_removed=False,
            desktop_entry=installer.DESKTOP_PATH,
            desktop_entry_removed=False,
        ),
    )
    installer.cli_uninstall(_ns())
    out = capsys.readouterr().out
    assert "nothing to delete" in out
