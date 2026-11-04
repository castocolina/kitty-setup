"""Subprocess tests for ``tools/uninstall.sh`` (R1.3, D-06, D-07).

Python is the stack (``AGENTS.md`` "Stack"), so the bootstrap shell script is
exercised from pytest with ``subprocess``, not with bats, and shellcheck is not
a test instrument here (D-07).

Safety property of the whole module: every run gets a complete replacement
environment built from literals and ``tmp_path`` values -- a fake ``HOME``, and
a fake ``PATH`` whose only non-system entry is a sandbox ``bin`` directory. The
module never reads the real environment (no ``os.environ | {...}`` merge, no
copy, no single-key read), so the developer's real ``HOME`` and real installed
``my-kitty`` are unreachable. ``bash`` itself is resolved through that sandbox
``PATH``. Every run passes ``KITTI_FORCE=1`` except the will-remove case, which
answers ``n`` to the real prompt; the script aborts there before it looks up any
binary.

Stubs echo their own argv, which is how the flag-forwarding cases assert without
a real binary. ``cwd`` is the repo root derived from this file's own location,
so the cases exercise the script of whichever tree they sit in.

Lives under ``tests/unit/``: it needs only ``bash``, no kitty, and the
integration tree is skipped unless ``KITTI_INTEGRATION=1`` (``tests/conftest.py``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SCRIPT: Final[Path] = REPO_ROOT / "tools" / "uninstall.sh"
RUN_TIMEOUT_S: Final[float] = 30.0
TAG: Final[str] = "[uninstall]"
LEGACY_NOTICE: Final[str] = "using legacy binary"
COMPLETION_LINE: Final[str] = (
    "  - ~/.local/share/kitty-setup/{my-kitty-completion.bash,_my-kitty,my-kitty-completion.zsh}"
)
STUB: Final[str] = '#!/usr/bin/env bash\nprintf \'STUB %s invoked: %s\\n\' "$0" "$*"\nexit 0\n'


class Sandbox:
    """A fake ``HOME`` (with an empty ``~/.local/bin``) and a fake ``bin`` directory."""

    def __init__(self, root: Path) -> None:
        self.home: Path = root / "home"
        self.local_bin: Path = self.home / ".local" / "bin"
        self.fake_bin: Path = root / "bin"
        self.local_bin.mkdir(parents=True)
        self.fake_bin.mkdir()

    def stub(self, directory: Path, name: str) -> Path:
        path = directory / name
        path.write_text(STUB, encoding="utf-8")
        path.chmod(0o755)
        return path

    def run(
        self, extra: dict[str, str] | None = None, *, force: bool = True, stdin: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        env: dict[str, str] = {
            "HOME": str(self.home),
            "PATH": f"{self.fake_bin}:/usr/bin:/bin",
        }
        if force:
            env["KITTI_FORCE"] = "1"
        env.update(extra or {})
        return subprocess.run(
            ["bash", str(SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
            input=stdin,
            env=env,
            timeout=RUN_TIMEOUT_S,
            cwd=str(REPO_ROOT),
        )


@pytest.fixture
def sandbox(tmp_path: Path) -> Sandbox:
    return Sandbox(tmp_path)


def _stub_line(binary: Path, args: str) -> str:
    return f"STUB {binary} invoked: {args}\n"


def _assert_diagnostics_on_stderr(result: subprocess.CompletedProcess[str]) -> None:
    """Every ``[uninstall]`` line is on stderr; stdout carries only the forwarded output."""
    assert TAG not in result.stdout, f"stdout={result.stdout!r}"
    assert f"{TAG} KITTI_FORCE=1 set; skipping interactive confirm" in result.stderr
    assert f"{TAG} done" in result.stderr


def test_legacy_binary_branch_forwards_to_my_kitty_setup(sandbox: Sandbox) -> None:
    """Only the legacy name exists. Before the D-06 fix this exits 127: the log line
    contaminates ``$(resolve_binary)`` and the script executes the whole string."""
    legacy = sandbox.stub(sandbox.fake_bin, "my-kitty-setup")
    result = sandbox.run()
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert result.stdout == _stub_line(legacy, "uninstall")
    assert LEGACY_NOTICE in result.stderr
    assert LEGACY_NOTICE not in result.stdout
    _assert_diagnostics_on_stderr(result)


def test_error_branch_diagnostics_are_visible_on_stderr(sandbox: Sandbox) -> None:
    """No binary anywhere: exit 1 together with both diagnostic lines the user can read."""
    result = sandbox.run()
    assert result.returncode == 1, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert (
        f"{TAG} ERROR: neither my-kitty nor my-kitty-setup found on PATH or in ~/.local/bin"
        in result.stderr
    )
    assert f"{TAG}        run 'make install' first, or remove manually" in result.stderr
    assert "STUB" not in result.stdout


def test_preferred_binary_wins_over_legacy(sandbox: Sandbox) -> None:
    preferred = sandbox.stub(sandbox.fake_bin, "my-kitty")
    sandbox.stub(sandbox.fake_bin, "my-kitty-setup")
    result = sandbox.run()
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert result.stdout == _stub_line(preferred, "uninstall")
    assert LEGACY_NOTICE not in result.stderr
    assert LEGACY_NOTICE not in result.stdout
    _assert_diagnostics_on_stderr(result)


def test_home_local_bin_fallback_is_used(sandbox: Sandbox) -> None:
    """``my-kitty`` only in the fake ``~/.local/bin``, not on the fake ``PATH``."""
    fallback = sandbox.stub(sandbox.local_bin, "my-kitty")
    result = sandbox.run()
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert result.stdout == _stub_line(fallback, "uninstall")
    _assert_diagnostics_on_stderr(result)


@pytest.mark.parametrize(
    ("variable", "flag"),
    [
        ("KEEP_BACKUPS", "--keep-backups"),
        ("KEEP_CONFIG", "--keep-config"),
        ("KEEP_KITTY", "--keep-kitty"),
    ],
)
def test_keep_env_forwards_as_flag(sandbox: Sandbox, variable: str, flag: str) -> None:
    binary = sandbox.stub(sandbox.fake_bin, "my-kitty")
    result = sandbox.run({variable: "1"})
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert result.stdout == _stub_line(binary, f"uninstall {flag}")
    _assert_diagnostics_on_stderr(result)


def test_will_remove_list_names_the_completion_file_unless_keep_kitty(
    sandbox: Sandbox,
) -> None:
    """Answer ``n`` to the real prompt and read the list the user would see.

    ``my-kitty uninstall`` removes the completion file under ``do_kitty``
    (``installer.cli_uninstall``), so the prompt must list it whenever ``KEEP_KITTY``
    is unset, and must not list it under ``KEEP_KITTY=1``. Answering ``n`` aborts in
    ``confirm``, before ``resolve_binary`` runs, so no binary is executed.
    """
    sandbox.stub(sandbox.fake_bin, "my-kitty")

    result = sandbox.run(force=False, stdin="n\n")
    assert result.returncode == 1, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "STUB" not in result.stdout
    assert "About to remove" in result.stdout
    assert COMPLETION_LINE in result.stdout.splitlines()

    kept = sandbox.run({"KEEP_KITTY": "1"}, force=False, stdin="n\n")
    assert kept.returncode == 1, f"stdout={kept.stdout!r} stderr={kept.stderr!r}"
    assert "STUB" not in kept.stdout
    assert "About to remove (preserving: kitty)" in kept.stdout
    assert "my-kitty-completion" not in kept.stdout


ASIDE_LINE: Final[str] = (
    "  - payload asides ~/.config/kitty/kitty-setup.rollback* left by interrupted installs"
)


def test_will_remove_list_names_payload_asides_unless_kept(sandbox: Sandbox) -> None:
    """The prompt names the payload asides by default and not under either keep flag (02-15).

    A full uninstall removes them, so the list must say so; ``KEEP_BACKUPS=1`` and
    ``KEEP_CONFIG=1`` keep them, so the list must not promise their removal.
    """
    sandbox.stub(sandbox.fake_bin, "my-kitty")

    default = sandbox.run(force=False, stdin="n\n")
    assert default.returncode == 1, f"stderr={default.stderr!r}"
    assert ASIDE_LINE in default.stdout.splitlines()

    kept_backups = sandbox.run({"KEEP_BACKUPS": "1"}, force=False, stdin="n\n")
    assert kept_backups.returncode == 1, f"stderr={kept_backups.stderr!r}"
    assert ASIDE_LINE not in kept_backups.stdout.splitlines()

    kept_config = sandbox.run({"KEEP_CONFIG": "1"}, force=False, stdin="n\n")
    assert kept_config.returncode == 1, f"stderr={kept_config.stderr!r}"
    assert ASIDE_LINE not in kept_config.stdout.splitlines()
