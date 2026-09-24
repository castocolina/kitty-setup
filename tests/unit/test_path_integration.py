"""Unit tests for ``kitty_setup.path_integration``."""

from __future__ import annotations

from pathlib import Path

import pytest

from kitty_setup import installer, path_integration

# The pre-D-01 bodies a host may still carry between our markers. Literal text, never rendered by
# the code under test: they are what an upgrade must replace.
_HELPER_GUARD = "if command -v register-python-argcomplete >/dev/null 2>&1; then"
_HELPER_EVAL = '    eval "$(register-python-argcomplete my-kitty)"'
_HOST_PRE_D01_BODY = (_HELPER_GUARD, _HELPER_EVAL, "fi")
_EVAL_BODY = (path_integration.EXPORT_LINE, *_HOST_PRE_D01_BODY)
_USER_COMPINIT = "autoload -Uz compinit && compinit"


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


def test_completion_current_template_block_is_noop(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    rc.write_text(path_integration._block_text("zsh"))
    before = rc.read_text()
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is False
    assert result.skipped is False
    assert "already" in result.reason or "matches" in result.reason
    assert rc.read_text() == before


def test_rc_block_renders_path_export_and_completion_lines(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    text = (home / ".zshrc").read_text()
    assert path_integration.EXPORT_LINE in text
    assert path_integration.ZSH_COMPINIT_LINE in text
    assert path_integration.completion_source_line("zsh") in text


def test_completion_old_path_only_block_rewritten_and_moved_last_in_zsh(tmp_path: Path) -> None:
    """A stale zsh block followed by an executable line is rewritten *and* moved to the end."""
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    pre = "# my own stuff\nalias ll='ls -la'\n"
    post = "\n# trailing user content\nexport EDITOR=vim\n"
    old_body = path_integration.EXPORT_LINE
    old_block = f"{path_integration.MARKER_BEGIN}\n{old_body}\n{path_integration.MARKER_END}\n"
    rc.write_text(pre + old_block + post)
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is True
    assert result.reason == "rewrote rc block body to current template"
    text = rc.read_text()
    assert text == pre + post + path_integration._block_text("zsh")


def test_legacy_block_migrates_with_completion_line(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    legacy_body = path_integration.EXPORT_LINE
    legacy = (
        f"{path_integration._LEGACY_MARKER_BEGIN}\n"
        f"{legacy_body}\n"
        f"{path_integration._LEGACY_MARKER_END}\n"
    )
    rc.write_text(legacy)
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is True
    text = rc.read_text()
    assert path_integration.MARKER_BEGIN in text
    assert path_integration._LEGACY_MARKER_BEGIN not in text
    assert path_integration.completion_source_line("zsh") in text


def test_completion_block_appended_despite_user_authored_export(tmp_path: Path) -> None:
    """User's manual PATH line MUST NOT short-circuit block injection.

    The block carries the completion eval line in addition to the PATH
    export, so the presence of a user-authored PATH line elsewhere in the
    rc does not satisfy the contract. The block is appended; the user's
    line is left intact.
    """
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    pre = 'export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"\n'
    rc.write_text(pre)
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is True
    text = rc.read_text()
    assert text.startswith(pre)
    assert path_integration.MARKER_BEGIN in text
    assert path_integration.completion_source_line("zsh") in text


def test_completion_block_appended_despite_tilde_export(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    rc.write_text('export PATH="~/.local/bin:$PATH"\n')
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is True
    assert path_integration.completion_source_line("zsh") in rc.read_text()


def test_completion_block_appended_when_env_already_has_target(tmp_path: Path) -> None:
    """$PATH covering ~/.local/bin must NOT skip block injection — the block
    also carries the line that sources the completion script."""
    home = tmp_path / "home"
    home.mkdir()
    target = home / ".local" / "bin"
    target.mkdir(parents=True)
    result = path_integration.ensure_local_bin_in_path(
        home=home, shell="zsh", env_path=f"{target}:/usr/bin"
    )
    assert result.changed is True
    text = (home / ".zshrc").read_text()
    assert path_integration.MARKER_BEGIN in text
    assert path_integration.completion_source_line("zsh") in text


def test_completion_unsupported_shell_skips_with_honest_manual_lines(tmp_path: Path) -> None:
    """Amended D-13 / R1.7: the PATH export, then an explicit no-completion line, and never a
    completion line in another shell's syntax."""
    home = tmp_path / "home"
    home.mkdir()
    result = path_integration.ensure_local_bin_in_path(home=home, shell="fish", env_path="")
    assert result.skipped is True
    assert result.changed is False
    assert result.shell == "fish"
    assert isinstance(result.manual_lines, tuple)
    assert result.manual_lines[0] == path_integration.EXPORT_LINE
    assert any(
        "fish" in line and "completion is not set up" in line for line in result.manual_lines[1:]
    )
    bash_source = path_integration.completion_source_line("bash")
    assert all(bash_source not in line for line in result.manual_lines)
    assert not any("my-kitty-completion" in line for line in result.manual_lines)
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


# --- R1.1 / D-01: the rc block sources the generated completion file -------


def _block(body: tuple[str, ...] | list[str]) -> str:
    return "\n".join([path_integration.MARKER_BEGIN, *body, path_integration.MARKER_END]) + "\n"


def _without_our_block(text: str) -> str:
    """Return ``text`` with the current-marker block's lines removed."""
    lines = text.splitlines(keepends=True)
    begin = next(
        i for i, line in enumerate(lines) if line.rstrip() == path_integration.MARKER_BEGIN
    )
    end = next(i for i, line in enumerate(lines) if line.rstrip() == path_integration.MARKER_END)
    return "".join(lines[:begin] + lines[end + 1 :])


def _body_of_our_block(text: str) -> list[str]:
    lines = text.splitlines()
    begin = lines.index(path_integration.MARKER_BEGIN)
    end = lines.index(path_integration.MARKER_END)
    return lines[begin + 1 : end]


def test_completion_bash_body_sources_file_without_compdef(tmp_path: Path) -> None:
    body = path_integration._block_body_lines("bash")
    completion_file = installer.completion_script_path("bash", home=Path("$HOME"))
    assert body == (
        path_integration.EXPORT_LINE,
        f'[ -f "{completion_file}" ] && . "{completion_file}"',
    )
    assert path_integration.completion_source_line("bash") == body[1]
    assert not any("compdef" in line or "compinit" in line for line in body)

    home = tmp_path / "home"
    home.mkdir()
    result = path_integration.ensure_local_bin_in_path(home=home, shell="bash", env_path="")
    assert result.rc_file == home / ".bashrc"
    text = (home / ".bashrc").read_text()
    assert text == path_integration._block_text("bash")
    assert "compdef" not in text


def test_completion_zsh_body_self_initialises_then_sources() -> None:
    body = path_integration._block_body_lines("zsh")
    completion_file = installer.completion_script_path("zsh", home=Path("$HOME"))
    assert path_integration.ZSH_COMPINIT_LINE == (
        "(( $+functions[compdef] )) || { autoload -Uz compinit && compinit -i; }"
    )
    quoted = f'"{completion_file}"'
    assert body == (
        path_integration.EXPORT_LINE,
        path_integration.ZSH_COMPINIT_LINE,
        f"[ -f {quoted} ] && command -v compdef >/dev/null 2>&1 && . {quoted}",
    )
    assert path_integration.completion_source_line("zsh") == body[2]
    assert "my-kitty-completion.zsh" in body[2]
    assert "-D" not in body[1].split()


def test_completion_template_match_is_per_shell() -> None:
    for own, other in (("bash", "zsh"), ("zsh", "bash")):
        text = path_integration._block_text(own)
        bounds = (0, len(text.splitlines()))
        assert path_integration._block_body_matches_template(text, bounds, own) is True
        assert path_integration._block_body_matches_template(text, bounds, other) is False


def test_completion_host_pre_d01_body_rewritten_in_place_bash(tmp_path: Path) -> None:
    """This host's measured ``~/.bashrc:70-74`` body: guard / eval / fi, with no PATH export."""
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".bashrc"
    pre = '# user rc\nexport PATH="$HOME/.local/bin:$HOME/bin:$PATH"\n'
    post = "alias ll='ls -la'\n# end\n"
    rc.write_text(pre + _block(_HOST_PRE_D01_BODY) + post)
    result = path_integration.ensure_local_bin_in_path(home=home, shell="bash", env_path="")
    assert result.changed is True
    assert result.reason == "rewrote rc block body to current template"
    text = rc.read_text()
    assert text == pre + path_integration._block_text("bash") + post
    assert path_integration.completion_source_line("bash") in text
    assert "register-python-argcomplete" not in text


@pytest.mark.parametrize(
    "obsolete_body",
    [_EVAL_BODY, (path_integration.EXPORT_LINE,)],
    ids=["eval-body", "path-only-body"],
)
def test_completion_dual_markers_rewrite_retained_obsolete_body(
    tmp_path: Path, obsolete_body: tuple[str, ...]
) -> None:
    """H3: removing the legacy block must not let an obsolete retained body survive."""
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".bashrc"
    head = "# user head\n"
    middle = "alias ll='ls -la'\n"
    tail = "# user tail\n"
    rc.write_text(head + _legacy_block() + middle + _block(obsolete_body) + tail)
    result = path_integration.ensure_local_bin_in_path(home=home, shell="bash", env_path="")
    assert result.changed is True
    assert result.reason == "removed duplicate legacy marker"
    text = rc.read_text()
    assert "my-kitty-setup PATH" not in text
    assert text.count(path_integration.MARKER_BEGIN) == 1
    assert tuple(_body_of_our_block(text)) == path_integration._block_body_lines("bash")
    assert _without_our_block(text) == head + middle + tail


def test_completion_zsh_block_above_compinit_moves_to_end(tmp_path: Path) -> None:
    """H4: a current-template zsh block above a ``compinit`` registers nothing; move it last."""
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    pre = "# user zshrc\n"
    post = f"{_USER_COMPINIT}\nbindkey -e\n"
    rc.write_text(pre + path_integration._block_text("zsh") + post)
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", env_path="")
    assert result.changed is True
    assert result.reason == "moved rc block to end of file"
    text = rc.read_text()
    assert text == pre + post + path_integration._block_text("zsh")
    lines = text.splitlines()
    assert lines.index(_USER_COMPINIT) < lines.index(path_integration.MARKER_BEGIN)


def test_print_path_result_unsupported_shell_prints_manual_lines_without_completion(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = path_integration.PathEditResult(
        changed=False,
        skipped=True,
        rc_file=None,
        shell="fish",
        reason="unsupported shell: fish",
        manual_lines=(
            path_integration.EXPORT_LINE,
            "# completion is not set up for fish: my-kitty generates it for bash and zsh only",
        ),
    )
    installer._print_path_result(result)
    out = capsys.readouterr().out
    assert path_integration.EXPORT_LINE in out
    assert "completion is not set up for fish" in out
    assert "my-kitty-completion" not in out
