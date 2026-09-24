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
    for sub in (
        "install",
        "uninstall",
        "doctor",
        "prune",
        "keys",
        "window",
        "tab",
        "os-window",
        "help",
    ):
        assert sub in out


def test_help_subcommand_prints_help_and_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main(["help"])
    out = capsys.readouterr().out
    assert code == 0
    for sub in (
        "install",
        "uninstall",
        "doctor",
        "prune",
        "keys",
        "window",
        "tab",
        "os-window",
        "help",
    ):
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


_SCRATCH_BACKUP = "kitty.conf.bak.20260101T000000Z"


def _scratch_home_with_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``HOME`` at ``tmp_path`` holding one backup, so the real handler has work to do."""
    kitty_dir = tmp_path / ".config" / "kitty"
    kitty_dir.mkdir(parents=True)
    (kitty_dir / "kitty.conf").write_text("", encoding="utf-8")
    backup = kitty_dir / _SCRATCH_BACKUP
    backup.write_text("", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    return backup


def _record_prune_args(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, argparse.Namespace]:
    """Replace ``cli_prune`` with a recorder, so no backup is ever listed or deleted."""
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.pruner, "cli_prune", fake)
    return captured


@pytest.mark.parametrize("option", ["--keep", "--older-than"])
def test_prune_negative_value_is_an_argparse_usage_error(
    option: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``prune --backups <option> -1`` is argparse's usage error, exit 2 — not a traceback.

    The real handler runs against a scratch ``HOME`` with one backup. Before the fix, argparse
    accepted ``-1``, and ``pruner``'s library guard raised a ``ValueError`` that escaped
    ``cli.main`` (D-13).
    """
    backup = _scratch_home_with_backup(tmp_path, monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(["prune", "--backups", option, "-1"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "usage: my-kitty prune" in err
    assert f"argument {option}" in err
    assert "-1" in err
    assert backup.exists(), "a rejected value must not delete anything"


def test_guard_prune_zero_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zero is a valid ``--keep``: the check is non-negative, not positive."""
    captured = _record_prune_args(monkeypatch)
    assert cli.main(["prune", "--backups", "--keep", "0"]) == 0
    assert captured["args"].keep == 0
    assert cli.main(["prune", "--backups", "--older-than", "0"]) == 0
    assert captured["args"].older_than == 0


@pytest.mark.parametrize(
    ("argv", "attr", "value"),
    [
        (["--keep", "5"], "keep", 5),
        (["--older-than", "30"], "older_than", 30),
    ],
)
def test_guard_prune_valid_values(
    argv: list[str], attr: str, value: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A positive value still reaches the handler, as an ``int``, unchanged."""
    captured = _record_prune_args(monkeypatch)
    assert cli.main(["prune", "--backups", *argv]) == 0
    got = getattr(captured["args"], attr)
    assert type(got) is int
    assert got == value


@pytest.mark.parametrize(("option", "raw"), [("--keep", "abc"), ("--older-than", "x")])
def test_guard_prune_non_int(
    option: str,
    raw: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A non-integer is still argparse's standard invalid-int error, exit 2."""
    captured = _record_prune_args(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(["prune", "--backups", option, raw])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert f"argument {option}: invalid int value: '{raw}'" in err
    assert not captured, "the handler must not run"


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


def test_tab_accent_routes_to_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.scenes.accent, "cli_set_tab_accent", fake)
    code = cli.main(["tab", "accent", "#0066cc"])
    assert code == 0
    args = captured["args"]
    assert args.color == "#0066cc"
    assert args.active_fg is None
    assert args.inactive_fg is None
    assert args.match is None
    assert args.to is None


def test_tab_accent_passes_fg_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}
    monkeypatch.setattr(
        cli.scenes.accent, "cli_set_tab_accent",
        lambda a: captured.setdefault("a", a) and 0,
    )
    cli.main(["tab", "accent", "blue", "--active-fg", "white", "--inactive-fg", "#cccccc"])
    args = captured["a"]
    assert args.color == "blue"
    assert args.active_fg == "white"
    assert args.inactive_fg == "#cccccc"


def test_window_background_routes_to_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.scenes.background, "cli_set_window_background", fake)
    code = cli.main(["window", "background", "#001a33", "--match", "id:5"])
    assert code == 0
    args = captured["args"]
    assert args.color == "#001a33"
    assert args.match == "id:5"
    assert args.to is None


def test_os_window_font_size_routes_to_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leading-dash positional `-2` MUST be accepted by argparse as the value."""
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.scenes.font, "cli_set_os_window_font_size", fake)
    code = cli.main(["os-window", "font-size", "-2"])
    assert code == 0
    args = captured["args"]
    assert args.value == "-2"
    assert args.all is False
    assert args.to is None


def test_os_window_font_size_all_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}
    monkeypatch.setattr(
        cli.scenes.font, "cli_set_os_window_font_size",
        lambda a: captured.setdefault("a", a) and 0,
    )
    cli.main(["os-window", "font-size", "14", "--all"])
    args = captured["a"]
    assert args.value == "14"
    assert args.all is True


def test_os_window_opacity_routes_to_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, argparse.Namespace] = {}

    def fake(args: argparse.Namespace) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(cli.scenes.opacity, "cli_set_os_window_opacity", fake)
    code = cli.main(["os-window", "opacity", "0.7", "--toggle"])
    assert code == 0
    args = captured["args"]
    assert args.value == 0.7
    assert args.toggle is True
    assert args.all is False
    assert args.to is None
