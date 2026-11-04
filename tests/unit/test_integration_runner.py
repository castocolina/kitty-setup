"""Unit tests for ``kitty_setup.harness.integration_runner`` (R0.13).

Hermetic: no ``cage``, no display and no kitty. Every compositor here is a fake
written as a Python script under ``tmp_path`` (the Stack rule forbids shell in the
repo); the child inside it is real — the runner's own child entry point, which runs
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
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

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
    assert vars(rt)["_child"]([str(status), "--", *args]) == 1
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


# --------------------------------------------------------------------------- IN-02 (02-15)


@pytest.mark.parametrize(
    "argv",
    [
        ["--ignore", "tests/integration/test_x.py"],
        ["--deselect", "tests/integration/test_x.py::test_a"],
    ],
    ids=["ignore", "deselect"],
)
def test_selector_option_value_is_never_a_selector(argv: list[str], tmp_path: Path) -> None:
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "integration" / "test_x.py").write_text("", encoding="utf-8")
    assert _rt().build_pytest_args(argv, cwd=tmp_path) == ["tests/integration", *argv]


def test_selector_k_value_naming_a_path_is_not_a_usage_error(tmp_path: Path) -> None:
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    args = ["-k", "tests"]
    assert _rt().build_pytest_args(args, cwd=tmp_path) == ["tests/integration", *args]


@pytest.mark.parametrize(
    "argv", [["-q", "tests/unit"], ["-k", "x", "tests/unit"]], ids=["q_then_unit", "k_then_unit"]
)
def test_selector_flag_before_an_outside_path_still_refuses(
    argv: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rt = _rt()
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    def must_not_run() -> object:
        raise AssertionError("a refused argv reached the compositor lookup")

    monkeypatch.setattr(rt, "resolve_compositor", must_not_run)
    assert rt.main(argv) == 64


@pytest.mark.parametrize(
    "argv",
    [
        ["--cov", "-k", "tests"],
        ["--debug", "-k", "tests"],
        ["--cov", "tests/unit"],
        ["-xk", "tests"],
    ],
    ids=["cov_then_k", "debug_then_k", "cov_bare_value", "short_cluster"],
)
def test_selector_option_values_follow_argparse(argv: list[str], tmp_path: Path) -> None:
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    assert _rt().build_pytest_args(argv, cwd=tmp_path) == ["tests/integration", *argv]


# (argv, the option the message must name). The `=` spellings of a short option are measured in
# 02-15's SUMMARY: pytest's argparse strips the `=` and takes the rest as the value.
_BYPASS_CASES: list[tuple[list[str], str]] = [
    (["--noconftest"], "--noconftest"),
    (["--confcutdir=tests/integration"], "--confcutdir"),
    (["--confcutdir", "tests/integration"], "--confcutdir"),
    (["-o", "addopts=--noconftest"], "-o"),
    (["-oaddopts=--noconftest"], "-o"),
    (["--override-ini=addopts=--noconftest"], "--override-ini"),
    (["-c", "tests/integration/alt.ini"], "-c"),
    (["-ctests/integration/alt.ini"], "-c"),
    (["-xc", "tests/integration/alt.ini"], "-c"),
    (["--config-file=x.ini"], "--config-file"),
    (["@tests/integration/args.txt"], "@tests/integration/args.txt"),
    (["-k", "@tests/integration/args.txt"], "@tests/integration/args.txt"),
    (["-o=addopts=--noconftest"], "-o"),
    (["-c=tests/integration/alt.ini"], "-c"),
]
_BYPASS_IDS: list[str] = [
    "noconftest",
    "confcutdir_eq",
    "confcutdir_sep",
    "override_sep",
    "override_glued",
    "override_long_eq",
    "config_sep",
    "config_glued",
    "config_cluster",
    "config_file_eq",
    "argfile",
    "argfile_as_value",
    "override_eq_short",
    "config_eq_short",
]


@pytest.mark.parametrize(("argv", "option"), _BYPASS_CASES, ids=_BYPASS_IDS)
def test_selector_conftest_bypass_is_a_usage_error(
    argv: list[str], option: str, tmp_path: Path
) -> None:
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "integration" / "alt.ini").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "integration" / "args.txt").write_text("--noconftest\n", encoding="utf-8")
    rt = _rt()
    # Called directly, never through main: at RED nothing is refused, and main would then start
    # a compositor.
    with pytest.raises(rt.UsageError) as caught:
        rt.build_pytest_args(argv, cwd=tmp_path)
    message = str(caught.value)
    assert repr(option) in message, message
    assert "tests/conftest.py" in message, message
    _assert_no_forgery(message)


def test_selector_override_ini_of_another_key_is_allowed(tmp_path: Path) -> None:
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    argv = ["-o", "xfail_strict=true"]
    assert _rt().build_pytest_args(argv, cwd=tmp_path) == ["tests/integration", *argv]


def test_headless_env_scrubs_pytest_addopts() -> None:
    env = _rt().headless_env({"PYTEST_ADDOPTS": "--noconftest", "PATH": "/usr/bin"})
    assert "PYTEST_ADDOPTS" not in env
    assert env["PATH"] == "/usr/bin"


def test_selector_child_flag_never_reaches_the_child_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    """T-2-71: a leading ``--child`` in PYTEST_ARGS is a usage error, never the child entry."""
    rt = _rt()
    monkeypatch.chdir(tmp_path)
    received: list[list[str]] = []

    def spy(args: list[str]) -> int:
        received.append(list(args))
        return 0

    def must_not_run() -> object:
        raise AssertionError("--child reached the compositor lookup")

    monkeypatch.setattr(rt, "_child", spy)
    monkeypatch.setattr(rt, "resolve_compositor", must_not_run)

    assert rt.main(["--child", str(tmp_path / "status"), "--", "-q"]) == 64
    assert received == [], "PYTEST_ARGS reached the child entry point"
    err = capfd.readouterr().err
    assert "'--child'" in err, err
    _assert_no_forgery(err)


@dataclass(frozen=True)
class _FakeItem:
    """The two attributes the collection hook reads from a pytest item."""

    path: Path
    nodeid: str


def test_scope_backstop_refuses_items_outside_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Under KITTI_INTEGRATION=1 an item outside tests/integration/ is a usage error (IN-02)."""
    conftest = importlib.import_module("tests.conftest")
    root: Path = vars(conftest)["REPO_ROOT"]
    hook: Any = vars(conftest)["pytest_collection_modifyitems"]
    monkeypatch.setenv("KITTI_INTEGRATION", "1")
    inside = _FakeItem(
        root / "tests" / "integration" / "test_x.py", "tests/integration/test_x.py::t"
    )
    outside = _FakeItem(root / "tests" / "unit" / "test_u.py", "tests/unit/test_u.py::test_u1")
    with pytest.raises(pytest.UsageError, match="tests/integration/") as caught:
        hook(None, [inside, outside])
    assert "tests/unit/test_u.py::test_u1" in str(caught.value)


def test_scope_backstop_allows_integration_items(monkeypatch: pytest.MonkeyPatch) -> None:
    conftest = importlib.import_module("tests.conftest")
    root: Path = vars(conftest)["REPO_ROOT"]
    hook: Any = vars(conftest)["pytest_collection_modifyitems"]
    monkeypatch.setenv("KITTI_INTEGRATION", "1")
    inside = _FakeItem(
        root / "tests" / "integration" / "test_x.py", "tests/integration/test_x.py::t"
    )
    assert hook(None, [inside]) is None
