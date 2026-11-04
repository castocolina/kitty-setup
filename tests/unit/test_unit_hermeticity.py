"""Self-tests for the unit tree's host-effect guard (02-12 IN-08) and the A-2 child-env rules.

Each guard case runs a child pytest over a sandbox project under ``tmp_path``. The child's env is
built from literals and ``tmp_path`` only, never ``os.environ``. Each blocking case asserts the
abort: the child exits 1, its summary names the child test, its output names the event, and the
host effect did not happen. The two AST rules check the child-process env of the unit modules
that start one. This module reads no ``os.environ`` and runs no repo ``make``.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_ENVIRON_NAMES = frozenset({"environ", "environb", "getenv"})


def _layout(tmp_path: Path) -> tuple[Path, Path]:
    """A sandbox home with the footprint directories, an ``outside`` directory and a run dir."""
    home = tmp_path / "home"
    (home / ".config" / "kitty").mkdir(parents=True)
    (home / ".config" / "kitty-setup" / "scenes").mkdir(parents=True)
    (home / ".local" / "bin").mkdir(parents=True)
    (tmp_path / "outside").mkdir()
    run = tmp_path / "run"
    run.mkdir()
    return home, run


def _fake_exec(path: Path, marker: Path) -> None:
    """A ``#!`` script that writes ``marker`` when it runs."""
    path.write_text(
        f"#!{sys.executable}\nfrom pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _project(tmp_path: Path, child: str) -> Path:
    """A sandbox project holding this tree's conftest and one child test module."""
    proj = tmp_path / "proj"
    (proj / "tests" / "unit").mkdir(parents=True)
    shutil.copyfile(HERE / "conftest.py", proj / "tests" / "unit" / "conftest.py")
    (proj / "tests" / "unit" / "test_child.py").write_text(child, encoding="utf-8")
    return proj


def _child_env(home: Path, run: Path, **extra: str) -> dict[str, str]:
    return {"HOME": str(home), "XDG_RUNTIME_DIR": str(run), "PATH": "/usr/bin:/bin", **extra}


def _run_child(proj: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit", "-q", "-p", "no:cacheprovider"],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _assert_blocked(result: subprocess.CompletedProcess[str], test: str, needle: str) -> None:
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert f"FAILED tests/unit/test_child.py::{test}" in out or (
        f"ERROR tests/unit/test_child.py::{test}" in out
    ), out
    assert needle in out, out


def test_hermetic_guard_blocks_footprint_write(tmp_path: Path) -> None:
    home, run = _layout(tmp_path)
    target = home / ".config" / "kitty" / "x"
    proj = _project(
        tmp_path,
        f"""
from pathlib import Path

def test_write() -> None:
    Path({str(target)!r}).write_text("x", encoding="utf-8")
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_write", "for writing")
    assert not target.exists()


def test_hermetic_guard_blocks_footprint_exec(tmp_path: Path) -> None:
    home, run = _layout(tmp_path)
    marker = tmp_path / "marker"
    kitty = home / ".local" / "bin" / "kitty"
    _fake_exec(kitty, marker)
    proj = _project(
        tmp_path,
        f"""
import subprocess

def test_exec() -> None:
    subprocess.run([{str(kitty)!r}], check=False)
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_exec", "subprocess.Popen")
    assert not marker.exists()


def test_hermetic_guard_blocks_runtime_mkdir(tmp_path: Path) -> None:
    home, run = _layout(tmp_path)
    proj = _project(
        tmp_path,
        f"""
import tempfile

def test_mkdir() -> None:
    tempfile.mkdtemp(dir={str(run)!r})
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_mkdir", "os.mkdir")
    assert list(run.iterdir()) == []


def test_hermetic_guard_blocks_symlinked_exec(tmp_path: Path) -> None:
    home, run = _layout(tmp_path)
    marker = tmp_path / "marker"
    real = tmp_path / "outside" / "my-kitty"
    _fake_exec(real, marker)
    link = home / ".local" / "bin" / "my-kitty"
    link.symlink_to(real)
    proj = _project(
        tmp_path,
        f"""
import subprocess

def test_symlinked() -> None:
    subprocess.run([{str(link)!r}], check=False)
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_symlinked", "subprocess.Popen")
    assert not marker.exists()


def test_hermetic_guard_blocks_symlinked_conf_write(tmp_path: Path) -> None:
    home, run = _layout(tmp_path)
    target = tmp_path / "outside" / "dotfiles" / "kitty.conf"
    target.parent.mkdir()
    target.write_text("orig", encoding="utf-8")
    link = home / ".config" / "kitty" / "kitty.conf"
    link.symlink_to(target)
    proj = _project(
        tmp_path,
        f"""
def test_conf_write() -> None:
    with open({str(link)!r}, "w", encoding="utf-8") as fh:
        fh.write("pwned")
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_conf_write", "for writing")
    assert link.is_symlink()
    assert target.read_text(encoding="utf-8") == "orig"


@pytest.mark.parametrize("variant", ["home", "home_alias"])
def test_hermetic_guard_blocks_intermediate_symlink_write(tmp_path: Path, variant: str) -> None:
    home, run = _layout(tmp_path)
    outside_dir = tmp_path / "outside" / "linkdir"
    outside_dir.mkdir()
    (outside_dir / "file").write_text("orig", encoding="utf-8")
    (home / ".config" / "kitty" / "linked").symlink_to(outside_dir)
    child_home = home
    if variant == "home_alias":
        child_home = tmp_path / "alias"
        child_home.symlink_to(home)
    path = child_home / ".config" / "kitty" / "linked" / "file"
    proj = _project(
        tmp_path,
        f"""
def test_intermediate() -> None:
    with open({str(path)!r}, "w", encoding="utf-8") as fh:
        fh.write("pwned")
""",
    )
    result = _run_child(proj, _child_env(child_home, run))
    _assert_blocked(result, "test_intermediate", "for writing")
    assert (home / ".config" / "kitty" / "linked").is_symlink()
    assert (outside_dir / "file").read_text(encoding="utf-8") == "orig"


def test_hermetic_guard_blocks_protected_symlink_removal(tmp_path: Path) -> None:
    home, run = _layout(tmp_path)
    target = tmp_path / "outside" / "dotfiles" / "bashrc"
    target.parent.mkdir()
    target.write_text("keep", encoding="utf-8")
    link = home / ".bashrc"
    link.symlink_to(target)
    proj = _project(
        tmp_path,
        f"""
import os

def test_remove() -> None:
    os.remove({str(link)!r})
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_remove", "os.remove")
    assert link.is_symlink()
    assert target.read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("variant", ["home_config", "xdg_config"])
def test_hermetic_guard_blocks_scene_write(tmp_path: Path, variant: str) -> None:
    home, run = _layout(tmp_path)
    if variant == "home_config":
        scene = home / ".config" / "kitty-setup" / "scenes" / "x.toml"
        proj = _project(
            tmp_path,
            f"""
from pathlib import Path

def test_scene() -> None:
    Path({str(scene)!r}).write_text("x", encoding="utf-8")
""",
        )
        result = _run_child(proj, _child_env(home, run))
    else:
        xdg = tmp_path / "xdg"
        (xdg / "kitty-setup" / "scenes").mkdir(parents=True)
        scene = xdg / "kitty-setup" / "scenes" / "x.toml"
        proj = _project(
            tmp_path,
            f"""
from pathlib import Path
import pytest

def test_scene(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", {str(tmp_path / "elsewhere")!r})
    Path({str(scene)!r}).write_text("x", encoding="utf-8")
""",
        )
        result = _run_child(proj, _child_env(home, run, XDG_CONFIG_HOME=str(xdg)))
    _assert_blocked(result, "test_scene", "for writing")
    assert not scene.exists()


@pytest.mark.parametrize("variant", ["dot_slash", "path_entry"])
def test_hermetic_guard_blocks_cwd_relative_exec(tmp_path: Path, variant: str) -> None:
    home, run = _layout(tmp_path)
    marker = tmp_path / "marker"
    _fake_exec(home / ".local" / "bin" / "kitty", marker)
    if variant == "dot_slash":
        call = (
            f'subprocess.run(["./kitty"], cwd={str(home / ".local" / "bin")!r}, '
            'env={"PATH": "/usr/bin:/bin"}, timeout=30, check=False)'
        )
    else:
        call = (
            f'subprocess.run(["kitty"], cwd={str(home / ".local")!r}, '
            'env={"PATH": "bin"}, timeout=30, check=False)'
        )
    proj = _project(
        tmp_path,
        f"""
import subprocess

def test_relative() -> None:
    {call}
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_relative", "subprocess.Popen")
    assert not marker.exists()


@pytest.mark.parametrize("variant", ["execv", "posix_spawn"])
def test_hermetic_guard_blocks_bare_name_exec(tmp_path: Path, variant: str) -> None:
    home, run = _layout(tmp_path)
    marker = tmp_path / "marker"
    bin_dir = home / ".local" / "bin"
    _fake_exec(bin_dir / "kitty", marker)
    if variant == "execv":
        call = 'os.execv("kitty", ["kitty"])'
    else:
        call = 'os.waitpid(os.posix_spawn("kitty", ["kitty"], {}), 0)'
    proj = _project(
        tmp_path,
        f"""
import os
import pytest

def test_bare(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir({str(bin_dir)!r})
    {call}
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_bare", "os.exec" if variant == "execv" else "os.posix_spawn")
    assert not marker.exists()


def test_hermetic_guard_blocks_dir_fd_mutation(tmp_path: Path) -> None:
    home, run = _layout(tmp_path)
    proj = _project(
        tmp_path,
        f"""
import os

def test_fd() -> None:
    fd = os.open({str(home / ".config" / "kitty")!r}, os.O_RDONLY)
    try:
        os.mkdir("x", dir_fd=fd)
    finally:
        os.close(fd)
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_fd", "os.mkdir")
    assert not (home / ".config" / "kitty" / "x").exists()


@pytest.mark.parametrize("variant", ["os_open_relative", "deleted_dir_fd"])
def test_hermetic_guard_fails_closed(tmp_path: Path, variant: str) -> None:
    home, run = _layout(tmp_path)
    if variant == "os_open_relative":
        body = f"""
import os

def test_closed() -> None:
    fd = os.open({str(home / ".config" / "kitty")!r}, os.O_RDONLY)
    try:
        os.open("x", os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=fd)
    finally:
        os.close(fd)
"""
    else:
        body = f"""
import contextlib
import os
from pathlib import Path

def test_closed() -> None:
    gone = Path({str(tmp_path / "gone")!r})
    gone.mkdir()
    fd = os.open(gone, os.O_RDONLY)
    os.rmdir(gone)
    with contextlib.suppress(FileNotFoundError):
        os.mkdir("x", dir_fd=fd)
    os.close(fd)
"""
    proj = _project(tmp_path, body)
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_closed", "path context unresolved")


@pytest.mark.parametrize(
    ("variant", "call"),
    [
        ("getaddrinfo", 'sys.audit("socket.getaddrinfo", "example.invalid", 80, 0, 0, 0)'),
        ("gethostbyname", 'sys.audit("socket.gethostbyname", "example.invalid")'),
        ("gethostbyaddr", 'sys.audit("socket.gethostbyaddr", "192.0.2.1")'),
        ("getnameinfo", 'sys.audit("socket.getnameinfo", ("192.0.2.1", 80))'),
    ],
)
def test_hermetic_guard_blocks_lookup(tmp_path: Path, variant: str, call: str) -> None:
    home, run = _layout(tmp_path)
    proj = _project(
        tmp_path,
        f"""
import sys

def test_lookup() -> None:
    {call}
""",
    )
    result = _run_child(proj, _child_env(home, run))
    _assert_blocked(result, "test_lookup", f"socket.{variant}")


def test_hermetic_guard_allows_loopback_lookup(tmp_path: Path) -> None:
    home, run = _layout(tmp_path)
    proj = _project(
        tmp_path,
        """
import sys

def test_loopback() -> None:
    sys.audit("socket.getaddrinfo", None, 80, 0, 0, 0)
    sys.audit("socket.getaddrinfo", "localhost", 80, 0, 0, 0)
    sys.audit("socket.gethostbyname", "localhost")
    sys.audit("socket.gethostbyaddr", "127.0.0.1")
    sys.audit("socket.gethostbyaddr", "::1")
    sys.audit("socket.getnameinfo", ("127.0.0.1", 80))
""",
    )
    result = _run_child(proj, _child_env(home, run))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


@pytest.mark.parametrize("variant", ["write", "rmtree"])
def test_hermetic_guard_allows_tmp(tmp_path: Path, variant: str) -> None:
    home, run = _layout(tmp_path)
    if variant == "write":
        body = """
from pathlib import Path

def test_tmp(tmp_path: Path) -> None:
    (tmp_path / "f").write_text("x", encoding="utf-8")
"""
    else:
        body = """
import shutil
from pathlib import Path

def test_tmp(tmp_path: Path) -> None:
    tree = tmp_path / "t"
    tree.mkdir()
    (tree / "f").write_text("x", encoding="utf-8")
    shutil.rmtree(tree)
"""
    proj = _project(tmp_path, body)
    result = _run_child(proj, _child_env(home, run))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def _sandbox_violations(source: str) -> list[str]:
    """The child-env part of A-2: every ``subprocess.run`` passes env, timeout and cwd, and no
    code reads the process environment (``os.environ``, ``os.environb``, ``os.getenv``, through any
    spelling, including ``from os import``)."""
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "subprocess.run":
            missing = {"env", "timeout", "cwd"} - {kw.arg for kw in node.keywords}
            if missing:
                found.append(f"line {node.lineno}: subprocess.run lacks {sorted(missing)}")
        if (
            isinstance(node, ast.Attribute)
            and node.attr in _ENVIRON_NAMES
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
        ):
            found.append(f"line {node.lineno}: reads os.{node.attr}")
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            found.extend(
                f"line {node.lineno}: imports {alias.name} from os"
                for alias in node.names
                if alias.name in _ENVIRON_NAMES
            )
    return found


def _uninstall_violations(source: str) -> list[str]:
    """The uninstall-only part of A-2, ported from map row 02-03-T1. Docstrings are exempt from the
    checks: the exact ``KITTI_FORCE`` member and the no-``shellcheck`` check read only the other
    string constants. ``test_tools_uninstall_sh.py`` names shellcheck in its module docstring."""
    tree = ast.parse(source)
    docstring_nodes = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    texts = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstring_nodes
    ]
    found = _sandbox_violations(source)
    if "KITTI_FORCE" not in texts:
        found.append('no exact "KITTI_FORCE" string constant outside the docstrings')
    found.extend(
        f"a non-docstring string mentions shellcheck: {text[:40]!r}"
        for text in texts
        if "shellcheck" in text
    )
    return found


def _source(name: str) -> str:
    return (HERE / name).read_text(encoding="utf-8")


def test_hermetic_uninstall_sandbox_rule_holds() -> None:
    assert _uninstall_violations(_source("test_tools_uninstall_sh.py")) == []


@pytest.mark.parametrize("module", ["test_makefile_clean.py", "test_unit_hermeticity.py"])
def test_hermetic_child_env_rule_holds(module: str) -> None:
    assert _sandbox_violations(_source(module)) == []


_ENVIRON_MERGE = """
import os, subprocess
subprocess.run(["x"], env=dict(os.environ), timeout=1, cwd=".")
"""

_RUN_WITHOUT_ENV = """
import subprocess
subprocess.run(["x"], timeout=1, cwd=".")
"""


def test_hermetic_uninstall_sandbox_rule_rejects_environ_merge() -> None:
    assert _sandbox_violations(_ENVIRON_MERGE) != []


def test_hermetic_uninstall_sandbox_rule_rejects_run_without_env() -> None:
    assert _sandbox_violations(_RUN_WITHOUT_ENV) != []
