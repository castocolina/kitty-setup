"""Unit tests for ``kitty_setup.harness.integration_runner`` (R0.13).

Hermetic: no ``cage``, no display and no kitty. Every compositor here is a fake
written as a Python script under ``tmp_path`` (the Stack rule forbids shell in the
repo); the child inside it is real — the runner's own ``--child`` mode, which runs
``sys.executable -m pytest`` over a two-line test file under ``tmp_path``, so the
repository's ``conftest.py`` and ``addopts`` do not apply.

The runner module is imported inside each test, not at module top, so that before
the module exists every case fails on its own (``ModuleNotFoundError``) instead of
the whole file collapsing into one collection error.

Case names carry the ``-k`` selectors 02-11-PLAN.md assigns: ``selector``,
``headless_env``, ``propagates`` and ``makefile`` (task 1); ``no_compositor``,
``runtime_dir``, ``always_zero``, ``missing_status``, ``leftover``, ``timeout`` and
``forge`` (task 2).
"""

from __future__ import annotations

import _thread
import importlib
import multiprocessing
import os
import re
import signal
import stat
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = REPO_ROOT / "Makefile"
RUNNER_MODULE = "kitty_setup.harness.integration_runner"

# A pytest summary token. The runner's own text must never contain one, so no gate
# that parses pytest's summary can be satisfied or tripped by the wrapper.
_PASSED_TOKEN = re.compile(r"(^|[^0-9])[0-9]+ passed", re.MULTILINE)
_FAILED_TOKEN = re.compile(r"[0-9]+ (failed|error)")

_SCRUBBED: tuple[str, ...] = (
    "WAYLAND_DISPLAY",
    "WAYLAND_SOCKET",
    "DISPLAY",
    "KITTY_LISTEN_ON",
    "KITTY_WINDOW_ID",
    "KITTY_PID",
    "KITTY_PUBLIC_KEY",
)

# Shared head of every fake compositor: record its own pid, find the child argv
# after the first `--`, the same shape `cage -- <cmd>` receives.
_PRELUDE = """
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = Path(__file__).name
(HERE / (NAME + ".pid")).write_text(str(os.getpid()), encoding="utf-8")
CHILD = sys.argv[sys.argv.index("--") + 1 :]
SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]


def spawn_sleeper() -> None:
    sleeper = subprocess.Popen(SLEEPER)
    (HERE / (NAME + ".sleeper.pid")).write_text(str(sleeper.pid), encoding="utf-8")
"""

_PASSTHROUGH = "sys.exit(subprocess.run(CHILD, check=False).returncode)\n"
_ALWAYS_ZERO = "subprocess.run(CHILD, check=False)\nsys.exit(0)\n"
_NO_CHILD = "sys.stderr.write('fake compositor: backend ready\\n')\nsys.exit(0)\n"
_LEAVES_SLEEPER = "spawn_sleeper()\nsys.exit(subprocess.run(CHILD, check=False).returncode)\n"
_HANGS = "spawn_sleeper()\ntime.sleep(60)\n"
_MARKS_IF_RUN = "(HERE / 'was-run').write_text('yes', encoding='utf-8')\nsys.exit(99)\n"


def _rt() -> ModuleType:
    return importlib.import_module(RUNNER_MODULE)


def _fake_compositor(tmp_path: Path, body: str, *, name: str = "cage") -> Path:
    """Write an executable Python fake compositor at ``tmp_path/bin/<name>``."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / name
    script.write_text(f"#!{sys.executable}\n{_PRELUDE}\n{body}", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


def _pytest_case(tmp_path: Path, *, passing: bool) -> list[str]:
    """Write a one-test file under ``tmp_path`` and return pytest args for it."""
    assertion = "True" if passing else "False"
    (tmp_path / "test_case_file.py").write_text(
        f"def test_case() -> None:\n    assert {assertion}\n", encoding="utf-8"
    )
    return ["test_case_file.py", "-q", "-p", "no:cacheprovider"]


def _environ(tmp_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["XDG_RUNTIME_DIR"] = str(tmp_path)
    return env


def _pid_file(script: Path, suffix: str) -> int:
    return int((script.parent / f"{script.name}{suffix}").read_text(encoding="utf-8"))


def _alive(pid: int) -> bool:
    """True when ``pid`` exists and is not a zombie."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    return fields.rsplit(")", 1)[1].split()[0] != "Z"


def _gone(pid: int, timeout_s: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not _alive(pid):
            return True
        time.sleep(0.05)
    return not _alive(pid)


def _assert_no_forgery(text: str) -> None:
    assert _PASSED_TOKEN.search(text) is None, text
    assert _FAILED_TOKEN.search(text) is None, text


def _run(tmp_path: Path, compositor: Path, pytest_args: list[str], **kwargs: float) -> int:
    rt = _rt()
    kwargs.setdefault("grace_s", 0.5)
    kwargs.setdefault("timeout_s", 60.0)
    result = rt.run(compositor, pytest_args, cwd=tmp_path, environ=_environ(tmp_path), **kwargs)
    assert isinstance(result, int)
    return result


def _recipe(target: str) -> list[str]:
    """Return the tab-indented recipe lines that follow ``<target>:`` in the Makefile."""
    lines = MAKEFILE.read_text(encoding="utf-8").splitlines()
    heads = [i for i, line in enumerate(lines) if line.startswith(f"{target}:")]
    assert len(heads) == 1, f"{target}: defined {len(heads)} times"
    recipe: list[str] = []
    for line in lines[heads[0] + 1 :]:
        if not line.startswith("\t"):
            break
        recipe.append(line)
    return recipe


# --------------------------------------------------------------------------- task 1


def test_selector_default_is_integration_root() -> None:
    assert _rt().build_pytest_args([]) == ["tests/integration"]


def test_selector_bare_k_never_widens_to_unit_tree() -> None:
    assert _rt().build_pytest_args(["-k", "cwd"]) == ["tests/integration", "-k", "cwd"]


def test_selector_integration_file_is_kept_unchanged(tmp_path: Path) -> None:
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "integration" / "test_h01_cwd.py").write_text("", encoding="utf-8")
    args = ["tests/integration/test_h01_cwd.py", "-q"]
    assert _rt().build_pytest_args(args, cwd=tmp_path) == args


def test_selector_node_id_suffix_is_stripped_before_the_path_check(tmp_path: Path) -> None:
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "integration" / "test_x.py").write_text("", encoding="utf-8")
    args = ["tests/integration/test_x.py::test_a", "-k", "a"]
    assert _rt().build_pytest_args(args, cwd=tmp_path) == args


@pytest.mark.parametrize("outside", ["tests/unit", "tests/integration/../unit", "tests"])
def test_selector_outside_integration_root_is_a_usage_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outside: str,
) -> None:
    rt = _rt()
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    assert rt.main([outside]) == 64
    assert rt.EXIT_USAGE == 64
    err = capsys.readouterr().err
    assert "tests/integration" in err
    assert outside in err
    _assert_no_forgery(err)


def test_headless_env_scrubs_display_and_kitty_remote_control() -> None:
    source: dict[str, str] = dict.fromkeys(_SCRUBBED, "live")
    source.update(
        {
            "PATH": "/usr/bin",
            "HOME": "/home/u",
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "KEEP_SESSIONS": "1",
            "KITTI_INTEGRATION": "0",
        }
    )
    before = dict(source)
    env = _rt().headless_env(source)
    for name in _SCRUBBED:
        assert name not in env, name
    assert env["WLR_BACKENDS"] == "headless"
    assert env["WLR_LIBINPUT_NO_DEVICES"] == "1"
    assert env["KITTI_INTEGRATION"] == "1"
    for kept in ("PATH", "HOME", "XDG_RUNTIME_DIR", "KEEP_SESSIONS"):
        assert env[kept] == source[kept]
    assert source == before, "headless_env mutated its input"


def test_propagates_passing_status_and_pytest_output(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    compositor = _fake_compositor(tmp_path, _PASSTHROUGH)
    assert _run(tmp_path, compositor, _pytest_case(tmp_path, passing=True)) == 0
    out, err = capfd.readouterr()
    assert re.search(r"(^|[^0-9])1 passed", out), out
    _assert_no_forgery(err)


def test_propagates_failing_status(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    compositor = _fake_compositor(tmp_path, _PASSTHROUGH)
    assert _run(tmp_path, compositor, _pytest_case(tmp_path, passing=False)) == 1
    out, err = capfd.readouterr()
    assert "1 failed" in out
    assert "pytest exit status 1" in err
    _assert_no_forgery(err)


def test_propagates_child_mode_writes_its_status_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = _rt()
    monkeypatch.chdir(tmp_path)
    status = tmp_path / "status"
    args = _pytest_case(tmp_path, passing=False)
    assert rt.main(["--child", str(status), "--", *args]) == 1
    assert status.read_text(encoding="utf-8").strip() == "1"


def test_makefile_has_one_line_test_integration_target() -> None:
    recipe = _recipe("test-integration")
    assert 1 <= len(recipe) <= 5
    joined = "\n".join(recipe)
    assert "python -m kitty_setup.harness.integration_runner" in joined
    assert "$(PYTEST_ARGS)" in joined


def test_makefile_phony_and_help_list_test_integration() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    phony = [line for line in text.splitlines() if line.startswith(".PHONY:")]
    assert len(phony) == 1
    assert "test-integration" in phony[0].split()
    help_lines = _recipe("help")
    assert any('"  test-integration ' in line for line in help_lines)
    assert not any("KITTI_INTEGRATION=1" in line for line in help_lines)


def test_makefile_test_recipe_is_unchanged() -> None:
    assert _recipe("test") == ["\t@uv run pytest tests/"]


# --------------------------------------------------------------------------- task 2


def test_no_compositor_on_path_fails_loudly_and_runs_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rt = _rt()
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert rt.resolve_compositor() is None
    assert rt.main([]) == 69
    assert rt.EXIT_UNAVAILABLE == 69
    out, err = capsys.readouterr()
    assert "no nested compositor" in err
    assert "looked for: cage" in err
    assert "NOT run" in err
    assert "a failure, not a skip" in err
    assert not (tmp_path / "tmp").exists(), "nothing may be spawned or logged"
    _assert_no_forgery(out + err)


def test_no_compositor_lookup_returns_an_absolute_path_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _fake_compositor(tmp_path, _MARKS_IF_RUN)
    monkeypatch.setenv("PATH", str(fake.parent))
    found = _rt().resolve_compositor()
    assert found == fake
    assert found.is_absolute()


@pytest.mark.parametrize("state", ["unset", "not-a-directory"])
def test_runtime_dir_missing_or_unusable_fails_before_spawning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    state: str,
) -> None:
    rt = _rt()
    fake = _fake_compositor(tmp_path, _MARKS_IF_RUN)
    monkeypatch.setenv("PATH", str(fake.parent))
    monkeypatch.chdir(tmp_path)
    if state == "unset":
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    else:
        not_a_dir = tmp_path / "a-file"
        not_a_dir.write_text("", encoding="utf-8")
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(not_a_dir))
    assert rt.main([]) == 69
    err = capsys.readouterr().err
    assert "XDG_RUNTIME_DIR" in err
    assert "NOT run" in err
    assert not (fake.parent / "was-run").exists(), "the compositor must not be started"
    _assert_no_forgery(err)


def test_always_zero_compositor_cannot_turn_a_failure_into_a_pass(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    compositor = _fake_compositor(tmp_path, _ALWAYS_ZERO)
    assert _run(tmp_path, compositor, _pytest_case(tmp_path, passing=False)) == 1
    out, err = capfd.readouterr()
    assert "1 failed" in out
    assert "pytest exit status 1" in err
    assert "compositor exited 0" in err
    _assert_no_forgery(err)


def test_missing_status_file_is_a_runner_failure_never_a_pass(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    rt = _rt()
    compositor = _fake_compositor(tmp_path, _NO_CHILD)
    assert _run(tmp_path, compositor, _pytest_case(tmp_path, passing=True)) == 70
    assert rt.EXIT_RUNNER_FAILURE == 70
    err = capfd.readouterr().err
    log = tmp_path / "tmp" / "test-integration" / "compositor.log"
    assert "status" in err
    assert "missing" in err
    assert str(log) in err
    assert "fake compositor: backend ready" in err, "the log tail must be printed"
    assert "fake compositor: backend ready" in log.read_text(encoding="utf-8")
    _assert_no_forgery(err)


def test_leftover_process_is_terminated_and_fails_the_run(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    compositor = _fake_compositor(tmp_path, _LEAVES_SLEEPER)
    started = time.monotonic()
    result = _run(tmp_path, compositor, _pytest_case(tmp_path, passing=True), grace_s=0.5)
    elapsed = time.monotonic() - started
    sleeper = _pid_file(compositor, ".sleeper.pid")
    assert _gone(sleeper), f"leftover pid {sleeper} survived the run"
    assert result == 70, "pytest passed, but a leftover process is a failure"
    out, err = capfd.readouterr()
    assert re.search(r"(^|[^0-9])1 passed", out), out
    assert "left" in err
    assert "terminated" in err
    assert elapsed < 10.0
    _assert_no_forgery(err)


def test_leftover_group_is_killed_on_keyboard_interrupt(tmp_path: Path) -> None:
    compositor = _fake_compositor(tmp_path, _HANGS)
    timer = threading.Timer(1.0, _thread.interrupt_main)
    timer.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            _run(tmp_path, compositor, _pytest_case(tmp_path, passing=True), timeout_s=30.0)
    finally:
        timer.cancel()
    assert _gone(_pid_file(compositor, ".pid"))
    assert _gone(_pid_file(compositor, ".sleeper.pid"))


def _main_in_fork(cwd: Path, path: str, runtime_dir: Path) -> None:
    """Forked-child entry point: run the runner's ``main`` the way ``make`` does."""
    os.chdir(cwd)
    os.environ["PATH"] = path
    os.environ["XDG_RUNTIME_DIR"] = str(runtime_dir)
    sys.exit(_rt().main(["-q"]))


def test_leftover_group_is_killed_when_the_runner_is_terminated(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    _rt()
    compositor = _fake_compositor(tmp_path, _HANGS)
    path = f"{compositor.parent}{os.pathsep}{os.environ.get('PATH', '')}"
    pid_file = compositor.parent / f"{compositor.name}.sleeper.pid"
    runner = multiprocessing.get_context("fork").Process(
        target=_main_in_fork, args=(tmp_path, path, tmp_path)
    )
    runner.start()
    try:
        deadline = time.monotonic() + 10.0
        while not pid_file.exists() and runner.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pid_file.exists(), "the fake compositor never started"
        runner.terminate()
        runner.join(timeout=15.0)
    finally:
        if runner.is_alive():
            runner.kill()
            runner.join()
    assert runner.exitcode == 128 + signal.SIGTERM
    assert _gone(_pid_file(compositor, ".pid"))
    assert _gone(_pid_file(compositor, ".sleeper.pid"))
    err = capfd.readouterr().err
    assert "terminated" in err
    _assert_no_forgery(err)


def test_timeout_kills_the_whole_group_and_fails_the_run(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    compositor = _fake_compositor(tmp_path, _HANGS)
    started = time.monotonic()
    result = _run(tmp_path, compositor, _pytest_case(tmp_path, passing=True), timeout_s=1.0)
    elapsed = time.monotonic() - started
    assert result == 70
    assert _gone(_pid_file(compositor, ".pid"))
    assert _gone(_pid_file(compositor, ".sleeper.pid"))
    err = capfd.readouterr().err
    assert "timeout" in err
    assert elapsed < 10.0
    _assert_no_forgery(err)


def test_forge_no_runner_message_carries_a_pytest_summary_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    rt = _rt()
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    def no_compositor() -> object:
        monkeypatch.setenv("PATH", str(tmp_path / "tests"))
        return rt.main([])

    def usage() -> object:
        return rt.main(["tests/unit"])

    def failing_child(label: str, body: str) -> Callable[[], object]:
        def go() -> object:
            case_dir = tmp_path / label
            case_dir.mkdir()
            compositor = _fake_compositor(case_dir, body)
            args = _pytest_case(case_dir, passing=False)
            return _run(case_dir, compositor, args, timeout_s=1.0)

        return go

    scenarios = [
        no_compositor,
        usage,
        failing_child("always-zero", _ALWAYS_ZERO),
        failing_child("missing-status", _NO_CHILD),
        failing_child("timeout", _HANGS),
    ]
    for scenario in scenarios:
        result = scenario()
        assert result != 0
    _assert_no_forgery(capfd.readouterr().err)
