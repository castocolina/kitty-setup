"""Unit tests for ``kitty_setup.path_integration``."""

from __future__ import annotations

import contextlib
import io
from collections.abc import Callable
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="bash", )
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
    assert result.changed is False
    assert result.skipped is False
    assert "already" in result.reason or "matches" in result.reason
    assert rc.read_text() == before


def test_rc_block_renders_path_export_and_completion_lines(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
    text = (home / ".zshrc").read_text()
    assert path_integration.EXPORT_LINE in text
    assert path_integration.ZSH_COMPINIT_LINE in text
    assert path_integration.completion_source_line("zsh") in text


_ZSH_CURRENT = path_integration._block_text("zsh")
_ALREADY_CURRENT = "rc block already matches current template"
_REWRITTEN = "rewrote rc block body to current template"
_TRAILING_PYENV = 'export PATH="/opt/sdkman/bin:$PATH"\neval "$(pyenv init -)"\n'
_TRAILING_FRAMEWORK = 'source "$HOME/.framework/init.zsh"\n'
_PRE_USER = "# my own stuff\nalias ll='ls -la'\n"
_POST_USER = "\n# trailing user content\nexport EDITOR=vim\n"
_OLD_PATH_ONLY_BLOCK = (
    f"{path_integration.MARKER_BEGIN}\n{path_integration.EXPORT_LINE}\n"
    f"{path_integration.MARKER_END}\n"
)


@pytest.mark.parametrize(
    ("rc_text", "reason", "expected"),
    [
        pytest.param(
            _ZSH_CURRENT + _TRAILING_PYENV,
            _ALREADY_CURRENT,
            _ZSH_CURRENT + _TRAILING_PYENV,
            id="pyenv_sdkman",
        ),
        pytest.param(
            _ZSH_CURRENT + _USER_COMPINIT + "\n",
            _ALREADY_CURRENT,
            _ZSH_CURRENT + _USER_COMPINIT + "\n",
            id="compinit_after",
        ),
        pytest.param(
            _ZSH_CURRENT + _TRAILING_FRAMEWORK,
            _ALREADY_CURRENT,
            _ZSH_CURRENT + _TRAILING_FRAMEWORK,
            id="framework_after",
        ),
        pytest.param(
            _PRE_USER + _OLD_PATH_ONLY_BLOCK + _POST_USER,
            _REWRITTEN,
            _PRE_USER + _ZSH_CURRENT + _POST_USER,
            id="stale_body_rewritten",
        ),
    ],
)
def test_zsh_block_stays_in_place(
    tmp_path: Path, rc_text: str, reason: str, expected: str
) -> None:
    """A zsh block stays where the user put it, whatever runs after it (02-14, WR-05)."""
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    rc.write_text(rc_text, encoding="utf-8")
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh")
    assert result.reason == reason
    assert rc.read_text(encoding="utf-8") == expected


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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
    assert result.changed is True
    assert path_integration.completion_source_line("zsh") in rc.read_text()


def test_completion_block_appended_when_env_already_has_target(tmp_path: Path) -> None:
    """$PATH covering ~/.local/bin must NOT skip block injection — the block
    also carries the line that sources the completion script."""
    home = tmp_path / "home"
    home.mkdir()
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh")
    assert result.changed is True
    text = (home / ".zshrc").read_text()
    assert path_integration.MARKER_BEGIN in text
    assert path_integration.completion_source_line("zsh") in text


def test_completion_unsupported_shell_skips_with_honest_manual_lines(tmp_path: Path) -> None:
    """Amended D-13 / R1.7: the PATH export, then an explicit no-completion line, and never a
    completion line in another shell's syntax."""
    home = tmp_path / "home"
    home.mkdir()
    result = path_integration.ensure_local_bin_in_path(home=home, shell="fish", )
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
    first = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
    second = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
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
    first = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
    snapshot = rc.read_text()
    second = path_integration.ensure_local_bin_in_path(home=home, shell="zsh", )
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="bash", )
    assert result.rc_file == home / ".bashrc"
    text = (home / ".bashrc").read_text()
    assert text == path_integration._block_text("bash")
    assert "compdef" not in text


def test_zsh_body_adds_fpath() -> None:
    """The four zsh body lines, literal: the fpath line puts the script's directory on fpath."""
    body = path_integration._block_body_lines("zsh")
    assert body == (
        'export PATH="$HOME/.local/bin:$PATH"',
        'fpath=("$HOME/.local/share/kitty-setup" $fpath)',
        "(( $+functions[compdef] )) || { autoload -Uz compinit && compinit -i; }",
        '[ -f "$HOME/.local/share/kitty-setup/_my-kitty" ] && command -v compdef >/dev/null 2>&1'
        ' && . "$HOME/.local/share/kitty-setup/_my-kitty"',
    )
    assert path_integration.completion_source_line("zsh") == body[3]
    assert "_my-kitty" in body[3]
    assert "-D" not in body[2].split()


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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="bash", )
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
    result = path_integration.ensure_local_bin_in_path(home=home, shell="bash", )
    assert result.changed is True
    assert result.reason == "removed duplicate legacy marker"
    text = rc.read_text()
    assert "my-kitty-setup PATH" not in text
    assert text.count(path_integration.MARKER_BEGIN) == 1
    assert tuple(_body_of_our_block(text)) == path_integration._block_body_lines("bash")
    assert _without_our_block(text) == head + middle + tail


def test_zsh_upgrade_rewrites_in_place(tmp_path: Path) -> None:
    """The 02-02-era body (hard-coded) is rewritten between its markers, and nothing moves."""
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".zshrc"
    old_body = (
        'export PATH="$HOME/.local/bin:$PATH"',
        "(( $+functions[compdef] )) || { autoload -Uz compinit && compinit -i; }",
        '[ -f "$HOME/.local/share/kitty-setup/my-kitty-completion.zsh" ] && command -v compdef '
        '>/dev/null 2>&1 && . "$HOME/.local/share/kitty-setup/my-kitty-completion.zsh"',
    )
    rc.write_text(_block(old_body) + _USER_COMPINIT + "\n", encoding="utf-8")
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh")
    assert result.reason == "rewrote rc block body to current template"
    assert rc.read_text(encoding="utf-8") == _ZSH_CURRENT + _USER_COMPINIT + "\n"


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_duplicate_rc_blocks_converge(tmp_path: Path, shell: str) -> None:
    """IN-01: two current blocks converge in one install; the rest are no-ops (T-2-63)."""
    home = tmp_path / "home"
    home.mkdir()
    rc = home / (".bashrc" if shell == "bash" else ".zshrc")
    block = path_integration._block_text(shell)
    pre = "# user rc\n"
    post = "alias ll='ls -la'\n"
    rc.write_text(pre + block + post + block, encoding="utf-8")
    first = path_integration.ensure_local_bin_in_path(home=home, shell=shell)
    assert first.reason == "removed duplicate rc block"
    text = rc.read_text(encoding="utf-8")
    assert text == pre + block + post
    assert text.count(path_integration.MARKER_BEGIN) == 1
    for _ in range(2):
        again = path_integration.ensure_local_bin_in_path(home=home, shell=shell)
        assert again.changed is False
        assert again.reason == "rc block already matches current template"
    assert rc.read_text(encoding="utf-8") == text


@pytest.mark.parametrize(("shell", "rc_name"), [("bash", ".bashrc"), ("zsh", ".zshrc")])
def test_rc_non_utf8_survives(tmp_path: Path, shell: str, rc_name: str) -> None:
    """WR-06: a Latin-1 byte in the rc survives, and nothing raises (no text-mode I/O)."""
    home = tmp_path / "home"
    home.mkdir()
    original = b"# caf\xe9 alias\n"
    rc = home / rc_name
    rc.write_bytes(original)
    path_integration.ensure_local_bin_in_path(home=home, shell=shell)
    assert rc.read_bytes().startswith(original)


_MIXED_ENDINGS = b"# a\r\nalias x=1\rlone\nlast\r\n"


@pytest.mark.parametrize("case", ["bash_append", "zsh_rewrite_in_place"])
def test_rc_line_endings_kept(tmp_path: Path, case: str) -> None:
    """WR-06: CRLF, a lone CR and LF outside the block survive byte for byte. ASCII only."""
    home = tmp_path / "home"
    home.mkdir()
    if case == "bash_append":
        rc = home / ".bashrc"
        rc.write_bytes(_MIXED_ENDINGS)
        path_integration.ensure_local_bin_in_path(home=home, shell="bash")
        assert rc.read_bytes().startswith(_MIXED_ENDINGS)
        return
    pre = _MIXED_ENDINGS
    post = b"tail\rlone\r\n"
    rc = home / ".zshrc"
    rc.write_bytes(pre + _OLD_PATH_ONLY_BLOCK.encode("utf-8") + post)
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh")
    assert result.reason == _REWRITTEN
    assert rc.read_bytes() == pre + _ZSH_CURRENT.encode("utf-8") + post


_LEGACY_BEGIN: str = vars(path_integration)["_LEGACY_MARKER_BEGIN"]
_LEGACY_END: str = vars(path_integration)["_LEGACY_MARKER_END"]
_LEGACY_BLOCK_TEXT = f"{_LEGACY_BEGIN}\nlegacy body line\n{_LEGACY_END}\n"


@pytest.mark.parametrize(
    ("eol", "last_block", "reason"),
    [
        pytest.param(
            "\n",
            path_integration._block_text("bash")[:-1],
            "removed duplicate rc block",
            id="duplicate_lf",
        ),
        pytest.param(
            "\r\n",
            path_integration._block_text("bash")[:-1],
            "removed duplicate rc block",
            id="duplicate_crlf",
        ),
        pytest.param(
            "\r\n",
            _LEGACY_BLOCK_TEXT[:-1],
            "removed duplicate legacy marker",
            id="legacy_crlf",
        ),
    ],
)
def test_rc_unterminated_tail_removal(
    tmp_path: Path, eol: str, last_block: str, reason: str
) -> None:
    """WR-06 and IN-01: removing an unterminated last block keeps the line before it (bash)."""
    home = tmp_path / "home"
    home.mkdir()
    rc = home / ".bashrc"
    expected = "# pre\n" + path_integration._block_text("bash") + "alias keep=yes" + eol
    rc.write_bytes((expected + last_block).encode("utf-8"))
    result = path_integration.ensure_local_bin_in_path(home=home, shell="bash")
    assert result.reason == reason
    assert rc.read_bytes() == expected.encode("utf-8")


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


# --- R1.7 / D-13: the install report prints what path_integration computed ----------------


def _report(result: path_integration.PathEditResult) -> str:
    """What ``installer._print_path_result`` prints for ``result``."""
    printer: Callable[[path_integration.PathEditResult], None] = vars(installer)[
        "_print_path_result"
    ]
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        printer(result)
    return buffer.getvalue()


def _current_block(shell: str) -> str:
    render: Callable[[str], str] = vars(path_integration)["_block_text"]
    return render(shell)


# The five changed-branch reasons, each reached from a real ``~/.zshrc`` state. Every state uses
# the same rc path, so a report line that ignores the reason is the same line for all five.
_REASON_STATES: list[tuple[str, Callable[[], str], str]] = [
    (
        "removed-duplicate",
        lambda: _legacy_block() + "# divider\n" + _new_block(),
        "removed duplicate legacy marker",
    ),
    ("migrated-legacy", _legacy_block, "migrated legacy marker"),
    (
        "removed_duplicate_rc",
        lambda: _current_block("zsh") + _current_block("zsh"),
        "removed duplicate rc block",
    ),
    ("rewrote-body", _new_block, "rewrote rc block body to current template"),
    ("appended", lambda: "# user zshrc\nalias ll='ls -la'\n", "appended sentinel-bracketed block"),
]


def _drive(home: Path, rc_text: str) -> tuple[path_integration.PathEditResult, str]:
    (home / ".zshrc").write_text(rc_text, encoding="utf-8")
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh")
    return result, _report(result)


@pytest.mark.parametrize(
    ("rc_text", "expected"),
    [(state, reason) for _, state, reason in _REASON_STATES],
    ids=[name for name, _, _ in _REASON_STATES],
)
def test_path_report_reason_printed(
    tmp_path: Path, rc_text: Callable[[], str], expected: str
) -> None:
    """D-13: the changed branch prints the reason ``ensure_local_bin_in_path`` computed."""
    result, out = _drive(tmp_path, rc_text())
    assert result.changed is True
    assert result.reason == expected
    assert result.reason in out, out


def test_path_report_reason_lines_distinct(tmp_path: Path) -> None:
    """Five distinct reasons print five distinct lines, compared as a set.

    A generic line that happens to carry one reason's words, or none, collapses the set.
    """
    lines: set[str] = set()
    reasons: set[str] = set()
    for _, state, _ in _REASON_STATES:
        result, out = _drive(tmp_path, state())
        reasons.add(result.reason)
        lines.update(line.strip() for line in out.splitlines() if line.strip())
    assert len(reasons) == 5
    assert len(lines) == 5, lines


def test_path_report_hint_prints_each_manual_line_on_its_own(tmp_path: Path) -> None:
    """Amended D-13: every entry of ``manual_lines`` is a whole printed line, verbatim.

    Joined with ``'; '`` they read as one shell command in which a ``#`` entry comments out
    whatever follows it. None of them may be a bash source line for a fish user.
    """
    result = path_integration.ensure_local_bin_in_path(home=tmp_path, shell="fish")
    assert result.skipped is True
    assert len(result.manual_lines) >= 2
    out = _report(result)
    printed = [line.strip() for line in out.splitlines() if line.strip()]
    for entry in result.manual_lines:
        assert entry.strip() in printed, out
    assert any("fish" in line for line in printed if line not in result.manual_lines), out
    bash_source = path_integration.completion_source_line("bash")
    assert all(bash_source not in line for line in printed), out
    assert "my-kitty-completion" not in out


def test_guard_path_report_unchanged_says_nothing_needed(tmp_path: Path) -> None:
    """Guard (green at RED): a current block reports that nothing needed doing."""
    result, out = _drive(tmp_path, _current_block("zsh"))
    assert result.changed is False
    assert "already" in out


def test_guard_path_report_keeps_source_guidance(tmp_path: Path) -> None:
    """Guard (green at RED): a change still tells the user to ``source`` the rc file."""
    result, out = _drive(tmp_path, "# user zshrc\n")
    assert result.changed is True
    assert f"source {tmp_path / '.zshrc'}" in out
