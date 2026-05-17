"""Unit tests for ``kitty_setup.cli`` (the my-kitty subcommand dispatcher)."""

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
    for sub in ("install", "uninstall", "doctor", "prune", "keys", "window", "tab", "help"):
        assert sub in out


def test_help_subcommand_prints_help_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main(["help"])
    out = capsys.readouterr().out
    assert code == 0
    for sub in ("install", "uninstall", "doctor", "prune", "keys", "window", "tab", "help"):
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


def test_uninstall_default_no_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.installer, "cli_uninstall", fake)
    code = cli.main(["uninstall"])
    assert code == 0
    args = captured["args"]
    assert args.keep_backups is False
    assert args.keep_config is False
    assert args.keep_kitty is False


@pytest.mark.parametrize(
    "flag,attr",
    [
        ("--keep-backups", "keep_backups"),
        ("--keep-config", "keep_config"),
        ("--keep-kitty", "keep_kitty"),
    ],
)
def test_uninstall_each_keep_flag_flips_only_its_attr(
    monkeypatch: pytest.MonkeyPatch, flag: str, attr: str
) -> None:
    captured: dict[str, argparse.Namespace] = {}
    monkeypatch.setattr(cli.installer, "cli_uninstall", lambda a: captured.setdefault("a", a) and 0)
    cli.main(["uninstall", flag])
    args = captured["a"]
    for name in ("keep_backups", "keep_config", "keep_kitty"):
        assert getattr(args, name) is (name == attr)


def test_uninstall_all_three_flags_compose(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}
    monkeypatch.setattr(cli.installer, "cli_uninstall", lambda a: captured.setdefault("a", a) and 0)
    cli.main(["uninstall", "--keep-backups", "--keep-config", "--keep-kitty"])
    args = captured["a"]
    assert args.keep_backups is True
    assert args.keep_config is True
    assert args.keep_kitty is True


@pytest.mark.parametrize("legacy", ["--kitty", "--self"])
def test_uninstall_legacy_flags_rejected(capsys: pytest.CaptureFixture[str], legacy: str) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["uninstall", legacy])
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "unrecognized" in err.lower() or "invalid" in err.lower() or legacy in err


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


def test_main_invokes_argcomplete_autocomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_autocomplete(parser: argparse.ArgumentParser) -> None:
        captured["parser"] = parser

    monkeypatch.setattr(cli.argcomplete, "autocomplete", fake_autocomplete)
    monkeypatch.setattr(cli.doctor, "cli_doctor", lambda _args: 0)
    assert cli.main(["doctor"]) == 0
    assert isinstance(captured["parser"], argparse.ArgumentParser)


def test_cli_module_has_argcomplete_magic_comment() -> None:
    """`register-python-argcomplete` scans the first 1024 bytes for the marker."""
    src = Path(cli.__file__).read_bytes()[:1024]
    assert b"PYTHON_ARGCOMPLETE_OK" in src


def test_window_title_routes_to_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.scenes.title, "cli_set_window_title", fake)
    code = cli.main(["window", "title", "deploy logs"])
    assert code == 0
    args = captured["args"]
    assert args.text == "deploy logs"
    assert args.temporary is True  # default
    assert args.match is None
    assert args.to is None


def test_window_title_no_temporary_flips_default(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}
    monkeypatch.setattr(
        cli.scenes.title, "cli_set_window_title",
        lambda a: captured.setdefault("a", a) and 0,
    )
    cli.main(["window", "title", "--no-temporary", "sticky"])
    args = captured["a"]
    assert args.text == "sticky"
    assert args.temporary is False


def test_tab_title_routes_to_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.scenes.title, "cli_set_tab_title", fake)
    code = cli.main(["tab", "title", "monitoring"])
    assert code == 0
    args = captured["args"]
    assert args.text == "monitoring"
    assert args.match is None
    assert args.to is None
    # The tab subparser must NOT expose --temporary; the Namespace should not carry it.
    assert not hasattr(args, "temporary")


def test_tab_title_rejects_temporary_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["tab", "title", "--temporary", "anything"])
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "unrecognized" in err.lower() or "--temporary" in err


def test_window_title_match_and_to_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}
    monkeypatch.setattr(
        cli.scenes.title, "cli_set_window_title",
        lambda a: captured.setdefault("a", a) and 0,
    )
    cli.main([
        "window", "title", "x",
        "--match", "id:5",
        "--to", "unix:/tmp/kitty-9999",
    ])
    args = captured["a"]
    assert args.match == "id:5"
    assert args.to == "unix:/tmp/kitty-9999"
