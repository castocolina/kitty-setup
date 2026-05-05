"""Unit tests for ``kitty_setup.path_integration``."""

from __future__ import annotations

from pathlib import Path

from kitty_setup import path_integration


def test_rc_missing_writes_block(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is True
    assert result.skipped is False
    assert result.rc_file == home / ".zshrc"
    text = (home / ".zshrc").read_text()
    assert path_integration.MARKER_BEGIN in text
    assert path_integration.EXPORT_LINE in text
    assert path_integration.MARKER_END in text


def test_rc_with_unrelated_content_appends_block(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".bashrc"
    rc.write_text("# my bashrc\nalias ll='ls -la'\n")
    result = path_integration.ensure_local_bin_in_path(home=home, shell="bash", env_path="")
    assert result.changed is True
    assert result.rc_file == rc
    text = rc.read_text()
    assert text.startswith("# my bashrc\n")
    assert path_integration.MARKER_BEGIN in text


def test_rc_already_has_our_block_is_noop(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    block = (
        f"{path_integration.MARKER_BEGIN}\n"
        f"{path_integration.EXPORT_LINE}\n"
        f"{path_integration.MARKER_END}\n"
    )
    rc.write_text(block)
    before = rc.read_text()
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is False
    assert result.skipped is False
    assert "already" in result.reason
    assert rc.read_text() == before


def test_rc_has_user_authored_export_is_noop(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    rc.write_text('export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"\n')
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is False
    assert "rc file already" in result.reason


def test_rc_has_tilde_export_is_noop(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    rc.write_text('export PATH="~/.local/bin:$PATH"\n')
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is False


def test_current_env_already_has_target_is_noop(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    target = home / ".local" / "bin"
    target.mkdir(parents=True)
    result = path_integration.ensure_local_bin_in_path(
        home=home, shell="zsh", env_path=f"{target}:/usr/bin"
    )
    assert result.changed is False
    assert "current environment" in result.reason
    assert not (home / ".zshrc").exists()


def test_unsupported_shell_returns_skipped(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    result = path_integration.ensure_local_bin_in_path(home=home, shell="fish", env_path="")
    assert result.skipped is True
    assert result.changed is False
    assert result.shell == "fish"
    assert result.manual_line == path_integration.EXPORT_LINE
    assert not (home / ".config").exists()


def test_idempotent_double_run(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    first = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    second = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert first.changed is True
    assert second.changed is False
    assert (home / ".zshrc").read_text().count(path_integration.MARKER_BEGIN) == 1


# --- rename-cli-to-my-kitty migration cases --------------------------------


def _legacy_block() -> str:
    return (
        f"{path_integration._LEGACY_MARKER_BEGIN}\n"
        f"{path_integration.EXPORT_LINE}\n"
        f"{path_integration._LEGACY_MARKER_END}\n"
    )


def _new_block() -> str:
    return (
        f"{path_integration.MARKER_BEGIN}\n"
        f"{path_integration.EXPORT_LINE}\n"
        f"{path_integration.MARKER_END}\n"
    )


def test_migrates_legacy_marker_alone(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    rc.write_text(_legacy_block())
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is True
    assert "migrated legacy marker" in result.reason
    text = rc.read_text()
    assert path_integration.MARKER_BEGIN in text
    assert path_integration._LEGACY_MARKER_BEGIN not in text
    assert path_integration.EXPORT_LINE in text


def test_migrates_legacy_with_unrelated_content(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    rc.write_text(f"# user header\nalias ll='ls -la'\n{_legacy_block()}# trailing user line\n")
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is True
    text = rc.read_text()
    assert text.startswith("# user header\nalias ll='ls -la'\n")
    assert text.endswith("# trailing user line\n")
    assert path_integration.MARKER_BEGIN in text
    assert path_integration._LEGACY_MARKER_BEGIN not in text


def test_legacy_and_new_blocks_keep_new(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    rc.write_text(_legacy_block() + "# divider\n" + _new_block())
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is True
    assert "removed duplicate legacy marker" in result.reason
    text = rc.read_text()
    assert path_integration._LEGACY_MARKER_BEGIN not in text
    assert text.count(path_integration.MARKER_BEGIN) == 1
    assert "# divider" in text


def test_idempotent_after_migration(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    rc.write_text(_legacy_block())
    first = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    snapshot = rc.read_text()
    second = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert first.changed is True
    assert second.changed is False
    assert "already" in second.reason
    assert rc.read_text() == snapshot
