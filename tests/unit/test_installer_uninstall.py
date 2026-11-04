"""Unit tests for ``installer.cli_uninstall`` flag combinations.

Default scope removes everything; ``--keep-*`` flags preserve subsets.
Each test monkeypatches the four real-side-effect helpers
(``uninstall_config_only``, ``config_updater.list_backups``,
``pruner.delete_each``, ``remove_kitty_install``) and asserts which were
invoked. The self-removal banner ALWAYS prints.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from kitty_setup import cli, config_updater, installer, pruner

MAKEFILE = Path(__file__).resolve().parents[2] / "Makefile"


def _ns(**flags: bool) -> argparse.Namespace:
    return argparse.Namespace(
        keep_backups=flags.get("keep_backups", False),
        keep_config=flags.get("keep_config", False),
        keep_kitty=flags.get("keep_kitty", False),
    )


@pytest.fixture(autouse=True)
def isolated_completion_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep ``cli_uninstall``'s completion-script removal (plan 02-01) off the real ``HOME``.

    Without this, every default-flag case here would unlink the user's own
    ``~/.local/share/kitty-setup/my-kitty-completion.*``. ``raising=False`` because the
    constant is introduced by the same plan whose RED commit adds this guard.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        installer,
        "COMPLETION_DIR",
        tmp_path / ".local" / "share" / "kitty-setup",
        raising=False,
    )


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[object]]:
    """Patch the five side-effect helpers; record invocations.

    ``remove_completion`` records ``installer.remove_completion_script``, the
    completion-file removal plan 02-01 tied to ``do_kitty``.
    """
    record: dict[str, list[object]] = {
        "uninstall": [],
        "list_backups": [],
        "delete_each": [],
        "remove_kitty": [],
        "remove_completion": [],
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

    def fake_remove_completion(*, home: Path | None = None) -> list[Path]:
        record["remove_completion"].append(home)
        return []

    monkeypatch.setattr(config_updater, "uninstall", fake_uninstall)
    monkeypatch.setattr(config_updater, "list_backups", fake_list_backups)
    monkeypatch.setattr(pruner, "delete_each", fake_delete_each)
    monkeypatch.setattr(installer, "remove_kitty_install", fake_remove_kitty)
    monkeypatch.setattr(installer, "remove_completion_script", fake_remove_completion)
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


def _clean_recipe_uninstall_flags() -> list[str]:
    """The ``--keep-*`` flags the Makefile's ``clean`` recipe passes to ``my-kitty uninstall``.

    Read from the tab-indented lines under the one ``clean:`` target, so the case below
    follows the recipe rather than a hand-built namespace the Makefile might not match.
    """
    lines = MAKEFILE.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("clean:")]
    assert len(starts) == 1, f"expected exactly one clean: target, found {len(starts)}"
    recipe: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if not line.startswith("\t"):
            break
        recipe.append(line)
    uninstall = [line for line in recipe if "my-kitty uninstall" in line]
    assert len(uninstall) == 1, f"clean recipe={recipe!r}"
    return re.findall(r"--keep-[a-z]+", uninstall[0])


def test_clean_recipe_flags_keep_kitty_and_backups(calls: dict[str, list[object]]) -> None:
    """``make clean``'s own flags, through the real CLI parser and dispatch (D-04).

    Preserves ``kitty.app``, the ``~/.local/bin/kitty`` symlink and the desktop entry
    (``remove_kitty_install`` not called), every ``kitty.conf.bak.*`` (no backup listing
    or deletion) and the completion file (``remove_completion_script`` not called), while
    still stripping the config block and removing the payload directory.
    """
    rc = cli.main(["uninstall", *_clean_recipe_uninstall_flags()])
    assert rc == 0
    assert calls["list_backups"] == []
    assert calls["delete_each"] == []
    assert len(calls["uninstall"]) == 1
    assert calls["remove_kitty"] == []
    assert calls["remove_completion"] == []


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


# --- R1.7 / D-11: the install log is removed, not relocated -----------------


def test_install_log_producer_is_gone() -> None:
    """Tombstone (D-11): pins a deletion, not a behaviour.

    ``_record_install_log`` wrote the kitty version to ``<repo>/tmp/install.log``, which
    nothing in ``src/``, ``tests/``, ``tools/``, ``docs/`` or the Makefile reads, and which a
    ``uv tool install`` put inside uv's own tool venv. It existed only because a spec now
    frozen under ``.planning/legacy/openspec/`` asked for it. This case is a signpost for a
    future reader: the log was removed on purpose and must not come back under another name.
    """
    assert "_record_install_log" not in vars(installer)


def test_install_log_not_written_by_mocked_install(
    calls: dict[str, list[object]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tombstone (D-11): a mocked install writes no ``install.log`` under the repo root.

    Pins a deletion, not a behaviour. ``_repo_root`` is pointed at a scratch root, the kitty
    binary is a stub whose version is captured without running it, and the symlink, desktop
    entry and scene seeding are stubbed, so nothing reaches the real ``HOME``. The report's
    version still comes from the captured version, and ``_repo_root`` keeps its two remaining
    callers: the payload source and the seeded-scenes source.
    """
    scratch = tmp_path / "repo"
    scratch.mkdir()
    dest = tmp_path / "dest"
    kitty_bin = dest / installer.KITTY_APP_DIRNAME / "bin" / "kitty"
    kitty_bin.parent.mkdir(parents=True)
    kitty_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    kitty_bin.chmod(0o755)

    def fake_repo_root() -> Path:
        return scratch

    def fake_capture_version(kitty_bin: Path) -> str:
        return "kitty 9.9.9 stub"

    def fake_ensure_symlink(_target: Path, _link: Path) -> None:
        return None

    def fake_write_desktop_entry(*, kitty_bin: Path, icon_path: Path) -> None:
        del kitty_bin, icon_path

    def fake_seed_scenes() -> tuple[int, int]:
        return (0, 0)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(installer, "_repo_root", fake_repo_root)
    monkeypatch.setattr(installer, "_capture_version", fake_capture_version)
    monkeypatch.setattr(installer, "_ensure_symlink", fake_ensure_symlink)
    monkeypatch.setattr(installer, "_write_desktop_entry", fake_write_desktop_entry)
    monkeypatch.setattr(installer, "seed_scenes", fake_seed_scenes)

    report = installer.install(dest=dest, inject_config=False)

    assert report.version == "kitty 9.9.9 stub"
    assert report.skipped_kitty_install is True
    assert list(tmp_path.rglob("install.log")) == []
    assert not (scratch / "tmp").exists()
    payload_source: Path = vars(installer)["_payload_source"]()
    scenes_source: Path = vars(installer)["_scenes_source"]()
    assert payload_source in {scratch / "config" / "kitty", _bundled("_payload") / "kitty"}
    assert scenes_source in {scratch / "examples" / "scenes", _bundled("_scenes")}
    assert calls["uninstall"] == [] and calls["remove_kitty"] == []


# --- IN-03 / R1.5: payload asides are removed on a full uninstall, kept and named otherwise -----

_ASIDE_NAMES: tuple[str, ...] = (
    "kitty-setup.rollback",
    "kitty-setup.rollback.20261103T120000Z",
    "kitty-setup.rollback.20261103T120000Z.1",
)
_SYMLINK_ASIDE_NAME = "kitty-setup.rollback.20261103T120000Z.2"
_LOOKALIKE_NAMES: tuple[str, ...] = (
    "kitty-setup.rollback-mine",
    "kitty-setup.rollback.notes",
    "kitty-setup.rollbackX",
    "kitty-setup.rollback.20261103T120000Z.1.bak",
)


def _seed_payload_asides(tmp_path: Path) -> tuple[list[Path], list[Path], Path]:
    """The asides an interrupted install leaves under ``~/.config/kitty``, plus four look-alikes.

    Returns (the asides, the look-alikes, the marker file in the symlink's target). The ``.2``
    aside is a symlink to a directory outside the footprint, which a removal must unlink and
    never follow.
    """
    kitty_dir = tmp_path / ".config" / "kitty"
    kitty_dir.mkdir(parents=True)
    asides = [kitty_dir / name for name in _ASIDE_NAMES]
    for aside in asides:
        aside.mkdir()
    target = tmp_path / "dotfiles"
    target.mkdir()
    marker = target / "MARKER"
    marker.write_text("kept", encoding="utf-8")
    link = kitty_dir / _SYMLINK_ASIDE_NAME
    link.symlink_to(target, target_is_directory=True)
    looks = [kitty_dir / name for name in _LOOKALIKE_NAMES]
    for look in looks:
        look.mkdir()
    return [*asides, link], looks, marker


def _present(path: Path) -> bool:
    return path.is_symlink() or path.exists()


@pytest.mark.parametrize("keep_kitty", [False, True], ids=["default", "keep_kitty"])
def test_full_uninstall_removes_payload_asides(
    keep_kitty: bool,
    calls: dict[str, list[object]],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A full uninstall (no ``--keep-backups``/``--keep-config``) removes and names every aside."""
    asides, looks, marker = _seed_payload_asides(tmp_path)

    rc = installer.cli_uninstall(_ns(keep_kitty=keep_kitty))

    assert rc == 0
    for aside in asides:
        assert not _present(aside), f"{aside.name} survived a full uninstall"
    assert marker.read_text(encoding="utf-8") == "kept", "a symlinked aside's target was touched"
    for look in looks:
        assert look.is_dir(), f"{look.name} is not a payload aside and must survive"
    out = capsys.readouterr().out
    for aside in asides:
        assert f"removed payload aside {aside}" in out, aside.name


@pytest.mark.parametrize("case", ["keep_backups", "keep_config", "clean_recipe"])
def test_kept_payload_asides_are_named(
    case: str, tmp_path: Path, capsys: pytest.CaptureFixture[str], calls: dict[str, list[object]]
) -> None:
    """Each uninstall that keeps backups keeps every aside and names it: delete it by hand."""
    del calls
    asides, looks, _marker = _seed_payload_asides(tmp_path)
    if case == "clean_recipe":
        flags = _clean_recipe_uninstall_flags()
    else:
        flags = [f"--{case.replace('_', '-')}"]

    rc = cli.main(["uninstall", *flags])

    assert rc == 0
    for aside in [*asides, *looks]:
        assert _present(aside), f"{aside.name} was removed by {flags}"
    kept = [line for line in capsys.readouterr().out.splitlines() if "kept payload aside" in line]
    assert len(kept) == len(asides), kept
    for aside in asides:
        assert any(f"kept payload aside {aside}" in line for line in kept), aside.name
    assert all("delete it by hand" in line for line in kept), kept


def test_payload_aside_removal_failure_is_one_line(
    calls: dict[str, list[object]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A removal that fails names its aside on one stderr line; the rest of the uninstall runs."""
    asides, _looks, _marker = _seed_payload_asides(tmp_path)

    def denied(path: Path) -> None:
        raise OSError(13, "Permission denied", str(path))

    monkeypatch.setattr(config_updater, "discard_payload_aside", denied, raising=False)

    rc = installer.cli_uninstall(_ns())

    captured = capsys.readouterr()
    assert rc == 1
    failures = [line for line in captured.err.splitlines() if "payload aside" in line]
    assert len(failures) == len(asides), failures
    for aside in asides:
        assert any(str(aside) in line for line in failures), aside.name
    assert "uv tool uninstall my-kitty" in captured.out, "the self-removal banner must still print"
    assert len(calls["remove_kitty"]) == 1
    assert len(calls["remove_completion"]) == 1


def _bundled(name: str) -> Path:
    """Where a wheel install puts a force-included directory, next to ``installer.py``."""
    return Path(installer.__file__).resolve().parent / name
