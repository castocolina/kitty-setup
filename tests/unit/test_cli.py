"""Unit tests for ``kitty_setup.cli`` (the my-kitty-setup subcommand dispatcher)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from kitty_setup import cli


def test_top_level_help_lists_all_subcommands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for sub in ("install", "uninstall", "doctor", "prune", "help"):
        assert sub in out


def test_help_subcommand_prints_help_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main(["help"])
    out = capsys.readouterr().out
    assert code == 0
    for sub in ("install", "uninstall", "doctor", "prune", "help"):
        assert sub in out


def test_prune_routes_to_cli_prune(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.pruner, "cli_prune", fake)
    code = cli.main(["prune"])
    assert code == 0
    args = captured["args"]
    assert args.backups is False
    assert args.keep is None
    assert args.older_than is None
    assert args.all is False


def test_prune_backups_keep_routes_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}
    monkeypatch.setattr(cli.pruner, "cli_prune", lambda a: captured.setdefault("a", a) and 0)
    cli.main(["prune", "--backups", "--keep", "5"])
    args = captured["a"]
    assert args.backups is True
    assert args.keep == 5
    assert args.all is False


def test_prune_older_than_routes_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}
    monkeypatch.setattr(cli.pruner, "cli_prune", lambda a: captured.setdefault("a", a) and 0)
    cli.main(["prune", "--backups", "--older-than", "30"])
    args = captured["a"]
    assert args.backups is True
    assert args.older_than == 30


def test_prune_all_routes_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}
    monkeypatch.setattr(cli.pruner, "cli_prune", lambda a: captured.setdefault("a", a) and 0)
    cli.main(["prune", "--backups", "--all"])
    args = captured["a"]
    assert args.all is True


def test_prune_two_policy_flags_exit_non_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["prune", "--backups", "--keep", "3", "--older-than", "30"])
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "not allowed" in err or "argument" in err.lower()


def test_no_args_prints_help_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "install" in out


def test_unknown_subcommand_exits_non_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["whatever-doesnt-exist"])
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "whatever-doesnt-exist" in err or "invalid choice" in err


def test_install_routes_to_cli_install(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.installer, "cli_install", fake)
    code = cli.main(["install", "--no-config", "--dest", "/tmp/x"])
    assert code == 0
    args = captured["args"]
    assert args.no_config is True
    assert args.dest == Path("/tmp/x")


def test_uninstall_routes_to_cli_uninstall_with_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.installer, "cli_uninstall", fake)
    code = cli.main(["uninstall", "--kitty", "--self"])
    assert code == 0
    assert captured["args"].kitty is True
    assert captured["args"].self_ is True


def test_uninstall_default_scope_no_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.installer, "cli_uninstall", fake)
    code = cli.main(["uninstall"])
    assert code == 0
    assert captured["args"].kitty is False
    assert captured["args"].self_ is False


def test_doctor_routes_to_cli_doctor(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, int] = {"n": 0}

    def fake(_args: object) -> int:
        called["n"] += 1
        return 0

    monkeypatch.setattr(cli.doctor, "cli_doctor", fake)
    code = cli.main(["doctor"])
    assert code == 0
    assert called["n"] == 1


def test_handler_return_code_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli.doctor, "cli_doctor", lambda _args: 42)
    assert cli.main(["doctor"]) == 42
