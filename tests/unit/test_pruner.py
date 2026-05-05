"""Unit tests for ``kitty_setup.pruner``."""

from __future__ import annotations

import argparse
import datetime as _dt
import os
from pathlib import Path

import pytest

from kitty_setup import config_updater, pruner


def _make_backup(home: Path, ts: str, *, days_old: int = 0) -> Path:
    kitty_dir = home / ".config" / "kitty"
    kitty_dir.mkdir(parents=True, exist_ok=True)
    path = kitty_dir / f"kitty.conf.bak.{ts}"
    path.write_text("backup content")
    if days_old:
        mtime = (_dt.datetime.now(_dt.UTC) - _dt.timedelta(days=days_old)).timestamp()
        os.utime(path, (mtime, mtime))
    return path


def _patch_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))


def _args(**kw: object) -> argparse.Namespace:
    base: dict[str, object] = {"backups": False, "keep": None, "older_than": None, "all": False}
    base.update(kw)
    return argparse.Namespace(**base)


@pytest.fixture()
def home(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    h = tmp_path  # type: ignore[assignment] — pytest sends a tmp_path even though hint says factory
    _patch_home(monkeypatch, h)
    return h


# ---- pure helpers ---------------------------------------------------------


def test_prune_by_keep_keeps_n_most_recent() -> None:
    backups = [Path(f"kitty.conf.bak.2026010{i}T000000Z") for i in (1, 2, 3, 4, 5)]
    to_delete = pruner.prune_by_keep(backups, 2)
    assert [p.name for p in to_delete] == [
        "kitty.conf.bak.20260101T000000Z",
        "kitty.conf.bak.20260102T000000Z",
        "kitty.conf.bak.20260103T000000Z",
    ]


def test_prune_by_keep_zero_returns_all() -> None:
    backups = [Path("a"), Path("b")]
    assert pruner.prune_by_keep(backups, 0) == backups


def test_prune_by_keep_n_greater_than_len_returns_empty() -> None:
    backups = [Path("a"), Path("b")]
    assert pruner.prune_by_keep(backups, 5) == []


def test_prune_by_keep_negative_raises() -> None:
    with pytest.raises(ValueError):
        pruner.prune_by_keep([], -1)


def test_prune_all_returns_full_list() -> None:
    backups = [Path("a"), Path("b")]
    assert pruner.prune_all(backups) == backups


def test_prune_by_age_filters_by_mtime(tmp_path: Path) -> None:
    fresh = tmp_path / "kitty.conf.bak.20260101T000000Z"
    old = tmp_path / "kitty.conf.bak.20260102T000000Z"
    fresh.write_text("x")
    old.write_text("x")
    now = _dt.datetime.now(_dt.UTC)
    fresh_ts = now.timestamp()
    old_ts = (now - _dt.timedelta(days=60)).timestamp()
    os.utime(fresh, (fresh_ts, fresh_ts))
    os.utime(old, (old_ts, old_ts))
    result = pruner.prune_by_age([fresh, old], days=30)
    assert result == [old]


def test_prune_by_age_negative_raises() -> None:
    with pytest.raises(ValueError):
        pruner.prune_by_age([], days=-1)


def test_delete_each_unlinks_and_counts(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.write_text("x")
    b.write_text("x")
    assert pruner.delete_each([a, b]) == 2
    assert not a.exists() and not b.exists()


def test_delete_each_swallows_missing(tmp_path: Path) -> None:
    a = tmp_path / "a"
    a.write_text("x")
    missing = tmp_path / "ghost"
    assert pruner.delete_each([a, missing]) == 1


# ---- cli_prune ------------------------------------------------------------


def test_cli_prune_no_backups_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_home(monkeypatch, tmp_path)
    code = pruner.cli_prune(_args())
    assert code == 0
    assert "no backups under" in capsys.readouterr().out


def test_cli_prune_dry_run_lists_does_not_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_home(monkeypatch, tmp_path)
    a = _make_backup(tmp_path, "20260101T000000Z")
    b = _make_backup(tmp_path, "20260102T000000Z")
    c = _make_backup(tmp_path, "20260103T000000Z")
    code = pruner.cli_prune(_args())
    out = capsys.readouterr().out
    assert code == 0
    assert "dry run" in out
    assert all(p.exists() for p in (a, b, c))
    assert "3 backup(s)" in out


def test_cli_prune_default_keep_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_home(monkeypatch, tmp_path)
    paths = [_make_backup(tmp_path, f"2026010{i}T000000Z") for i in (1, 2, 3, 4, 5, 6, 7)]
    code = pruner.cli_prune(_args(backups=True))
    out = capsys.readouterr().out
    assert code == 0
    assert "policy: --keep 3" in out
    surviving = config_updater.list_backups(paths[0].parent / "kitty.conf")
    assert [p.name for p in surviving] == [p.name for p in paths[-3:]]
    assert "deleted 4" in out


def test_cli_prune_keep_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_home(monkeypatch, tmp_path)
    paths = [_make_backup(tmp_path, f"2026010{i}T000000Z") for i in (1, 2, 3, 4)]
    code = pruner.cli_prune(_args(backups=True, keep=1))
    out = capsys.readouterr().out
    assert code == 0
    surviving = sorted(
        p.name for p in paths[0].parent.iterdir() if p.name.startswith("kitty.conf.bak")
    )
    assert surviving == ["kitty.conf.bak.20260104T000000Z"]
    assert "deleted 3" in out


def test_cli_prune_older_than(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_home(monkeypatch, tmp_path)
    fresh1 = _make_backup(tmp_path, "20260101T000000Z", days_old=5)
    fresh2 = _make_backup(tmp_path, "20260102T000000Z", days_old=20)
    old1 = _make_backup(tmp_path, "20260103T000000Z", days_old=40)
    old2 = _make_backup(tmp_path, "20260104T000000Z", days_old=60)
    code = pruner.cli_prune(_args(backups=True, older_than=30))
    out = capsys.readouterr().out
    assert code == 0
    assert fresh1.exists() and fresh2.exists()
    assert not old1.exists() and not old2.exists()
    assert "deleted 2" in out


def test_cli_prune_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _patch_home(monkeypatch, tmp_path)
    paths = [_make_backup(tmp_path, f"2026010{i}T000000Z") for i in (1, 2, 3, 4, 5)]
    code = pruner.cli_prune(_args(backups=True, all=True))
    out = capsys.readouterr().out
    assert code == 0
    assert all(not p.exists() for p in paths)
    assert "deleted 5" in out


def test_cli_prune_does_not_touch_unrelated_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_home(monkeypatch, tmp_path)
    bak = _make_backup(tmp_path, "20260101T000000Z")
    notes = bak.parent / "my-notes.txt"
    notes.write_text("important")
    pruner.cli_prune(_args(backups=True, all=True))
    assert not bak.exists()
    assert notes.exists()
    assert notes.read_text() == "important"


def test_cli_prune_does_not_touch_malformed_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_home(monkeypatch, tmp_path)
    good = _make_backup(tmp_path, "20260101T000000Z")
    bad = good.parent / "kitty.conf.bak.notadate"
    bad.write_text("malformed")
    pruner.cli_prune(_args(backups=True, all=True))
    assert not good.exists()
    assert bad.exists()


def test_cli_prune_lists_only_when_no_policy_consumed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Sanity: dry run with backup files present must NOT delete anything even
    # when the directory has many.
    _patch_home(monkeypatch, tmp_path)
    paths = [_make_backup(tmp_path, f"2026010{i}T000000Z") for i in (1, 2, 3, 4, 5, 6, 7)]
    pruner.cli_prune(_args())
    assert all(p.exists() for p in paths)
