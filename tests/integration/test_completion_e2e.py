"""Real-shell proof that the rc block registers ``my-kitty`` completion (R1.1, D-01, H4).

Each case builds a throwaway ``HOME`` holding the completion file ``installer`` generates and an
rc rendered by ``path_integration``, then starts a real ``bash -i`` or ``zsh -i`` against it and
reads what the shell registered. It lives in the gated tree because it depends on host state —
which shells are installed (zsh here is a linuxbrew build, not system) and a resolvable
``my-kitty`` — which is what ``KITTI_INTEGRATION`` means. The *contract* is pinned by the ungated
unit tests in ``tests/unit/test_installer_completion.py``, ``tests/unit/test_path_integration.py``
and ``tests/unit/test_doctor.py``; nothing load-bearing hides behind the gate.

Every child gets a minimal environment: ``HOME`` and ``ZDOTDIR`` set to the case's home, ``PATH``
set to the shell's own directory plus ``/usr/bin:/bin``, ``TERM=dumb`` and stdin from
``/dev/null``. The narrow ``PATH`` keeps the venv's argcomplete helper out of reach, so no case
can pass through the runtime helper lookup D-01 deletes. Under ``make test-integration`` the
children have no controlling terminal: ``bash -i`` then prints job-control warnings on stderr, so
no case asserts that stderr is empty — only on the text a case is about.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from kitty_setup import doctor, installer, path_integration

_USER_COMPINIT = "autoload -Uz compinit && compinit"
_ZSH_PROBE = "print -r -- ${_comps[my-kitty]-<none>}"
_ARGCOMPLETE_FN = "_python_argcomplete"
_TIMEOUT_S = 30


def _require(path: str | None, name: str) -> str:
    """Skip the case when its shell is absent: there is nothing to prove without it."""
    if path is None:
        pytest.skip(f"{name} is not on PATH")
    return path


def _env(home: Path, shell_path: str) -> dict[str, str]:
    return {
        "HOME": str(home),
        "ZDOTDIR": str(home),
        "PATH": f"{Path(shell_path).parent}:/usr/bin:/bin",
        "TERM": "dumb",
    }


def _run(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
        check=False,
    )


def _home(tmp_path: Path, name: str, shell: str) -> Path:
    home = tmp_path / name
    home.mkdir()
    installer.write_completion_script(shell, home=home)
    return home


def _zsh_registrations(zsh: str, home: Path) -> list[subprocess.CompletedProcess[str]]:
    """Two consecutive starts, so the second reads the ``.zcompdump`` the first one wrote."""
    return [_run([zsh, "-i", "-c", _ZSH_PROBE], _env(home, zsh)) for _ in range(2)]


def _registered(starts: list[subprocess.CompletedProcess[str]]) -> bool:
    return all(start.stdout.strip() == _ARGCOMPLETE_FN for start in starts)


def test_bash_registers_completion_from_rendered_block(tmp_path: Path) -> None:
    bash = _require(shutil.which("bash"), "bash")
    home = _home(tmp_path, "home", "bash")
    (home / ".bashrc").write_text(path_integration._block_text("bash"), encoding="utf-8")
    proc = _run([bash, "-i", "-c", "complete -p my-kitty"], _env(home, bash))
    assert proc.returncode == 0, proc.stderr
    assert f"-F {_ARGCOMPLETE_FN} my-kitty" in proc.stdout


def test_zsh_registers_completion_after_user_compinit(tmp_path: Path) -> None:
    zsh = _require(shutil.which("zsh"), "zsh")
    home = _home(tmp_path, "home", "zsh")
    rc = f"{_USER_COMPINIT}\n" + path_integration._block_text("zsh")
    (home / ".zshrc").write_text(rc, encoding="utf-8")
    starts = _zsh_registrations(zsh, home)
    assert [s.stdout.strip() for s in starts] == [_ARGCOMPLETE_FN, _ARGCOMPLETE_FN]


def test_zsh_registers_completion_with_no_user_compinit(tmp_path: Path) -> None:
    zsh = _require(shutil.which("zsh"), "zsh")
    home = _home(tmp_path, "home", "zsh")
    body = path_integration._block_body_lines("zsh")
    assert path_integration.ZSH_COMPINIT_LINE in body
    (home / ".zshrc").write_text(path_integration._block_text("zsh"), encoding="utf-8")
    assert "compinit" not in (home / ".zshrc").read_text().replace(
        path_integration.ZSH_COMPINIT_LINE, ""
    )
    starts = _zsh_registrations(zsh, home)
    assert [s.stdout.strip() for s in starts] == [_ARGCOMPLETE_FN, _ARGCOMPLETE_FN]
    for start in starts:
        assert "command not found: compdef" not in start.stderr


def test_producer_protocol_returns_candidates_on_fd8(tmp_path: Path) -> None:
    """argcomplete writes candidates to fd 8, separated by ``\\013`` — not to stdout."""
    bash = _require(shutil.which("bash"), "bash")
    home = _home(tmp_path, "home", "bash")
    (home / ".bashrc").write_text(path_integration._block_text("bash"), encoding="utf-8")
    my_kitty = shutil.which("my-kitty")
    if my_kitty is None:
        pytest.fail("my-kitty is not resolvable from the test process; the venv is not on PATH")
    # The rendered block's own PATH export is what makes `my-kitty` resolvable in the child.
    (home / ".local" / "bin").mkdir(parents=True)
    (home / ".local" / "bin" / "my-kitty").symlink_to(my_kitty)
    script = (
        "_ARGCOMPLETE=1 _ARGCOMPLETE_IFS=$'\\013' COMP_LINE='my-kitty ' COMP_POINT=9 "
        "my-kitty 8>&1 1>/dev/null 2>/dev/null"
    )
    proc = _run([bash, "-i", "-c", script], _env(home, bash))
    candidates = [c.strip() for c in proc.stdout.split("\013") if c.strip()]
    assert candidates, (proc.returncode, proc.stdout, proc.stderr)
    assert "doctor" in candidates


def test_zsh_block_above_compinit_is_moved_by_install_and_registers(tmp_path: Path) -> None:
    """H4: install moves a current-template zsh block from above ``compinit`` to the end."""
    zsh = _require(shutil.which("zsh"), "zsh")
    home = _home(tmp_path, "home", "zsh")
    rc = home / ".zshrc"
    rc.write_text(path_integration._block_text("zsh") + f"{_USER_COMPINIT}\n", encoding="utf-8")
    result = path_integration.ensure_local_bin_in_path(home=home, shell="zsh")
    assert result.reason == "moved rc block to end of file"
    lines = rc.read_text(encoding="utf-8").splitlines()
    assert lines.index(_USER_COMPINIT) < lines.index(path_integration.MARKER_BEGIN)
    starts = _zsh_registrations(zsh, home)
    assert [s.stdout.strip() for s in starts] == [_ARGCOMPLETE_FN, _ARGCOMPLETE_FN]


def test_doctor_verdict_matches_real_zsh_registration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H4, doctor half: doctor's verdict equals what real zsh registers, across four shapes.

    Two shapes register and two do not, so a check and a shell that were wrong the same way
    cannot pass together. One function, not parametrized, so the RED count stays exact.
    """
    zsh = _require(shutil.which("zsh"), "zsh")
    monkeypatch.setenv("SHELL", zsh)
    block = path_integration._block_text("zsh")
    guard_only = "\n".join(
        [
            path_integration.MARKER_BEGIN,
            path_integration.EXPORT_LINE,
            path_integration.completion_source_line("zsh"),
            path_integration.MARKER_END,
        ]
    )
    shapes: dict[str, tuple[str, bool]] = {
        "S1 compinit then our block last": (f"{_USER_COMPINIT}\n{block}", True),
        "S2 our block last, no compinit": (block, True),
        "S3 our block above a compinit": (f"{block}{_USER_COMPINIT}\n", False),
        "S4 guard-only body last, no compinit": (f"{guard_only}\n", False),
    }
    for index, (shape, (rc_text, expected)) in enumerate(shapes.items()):
        home = _home(tmp_path, f"s{index + 1}", "zsh")
        (home / ".zshrc").write_text(rc_text, encoding="utf-8")
        verdict = doctor._check_completion(home=home)
        registered = _registered(_zsh_registrations(zsh, home))
        assert registered is expected, f"{shape}: zsh registered={registered}"
        assert verdict.passed is registered, f"{shape}: doctor said {verdict.render()!r}"
