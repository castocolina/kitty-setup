"""Headless runner for ``tests/integration/`` — the engine behind ``make test-integration`` (R0.13).

``make test`` skips every integration item unless ``KITTI_INTEGRATION=1`` (``tests/conftest.py``),
and setting that variable by hand runs real kitty sessions on the user's desktop. This runner
executes the suite inside a nested compositor instead, so no window reaches the desktop:

    uv run python -m kitty_setup.harness.integration_runner [PYTEST_ARGS...]

Contract, in the order the code enforces it:

* ``PYTEST_ARGS`` may only narrow the run. With no path selector the run is all of
  ``tests/integration``; a path selector outside it is a usage error (``EXIT_USAGE``). An option's
  value is never a selector; an option or ``@`` argument file that could stop pytest loading
  ``tests/conftest.py``, and ``--child``, are usage errors, and ``PYTEST_ADDOPTS`` is dropped;
  ``tests/conftest.py`` refuses any collected item outside ``tests/integration/``.
* No compositor on ``PATH``, or no usable ``XDG_RUNTIME_DIR``, is a loud failure
  (``EXIT_UNAVAILABLE``) — the suite was NOT run, and that is never reported as a skip.
* The compositor starts in its own session with the display and kitty remote-control
  variables scrubbed and stdin detached, so the run has no controlling terminal and cannot
  reach the user's live kitty.
* The verdict is pytest's own exit status, written by this module's child entry point, which
  ``run()`` starts as a ``-c`` program and ``main`` never reaches, into a status file inside the
  compositor. The compositor's exit status is recorded, never returned:
  a wrapper that exits 0 regardless would otherwise turn every failure into a pass. A missing
  status file, a timeout, or a process left behind is ``EXIT_RUNNER_FAILURE``.
* The compositor's process group is terminated on every exit path, including interrupt,
  ``SIGTERM`` and ``SIGHUP``.

The runner's own messages go to stderr, prefixed ``test-integration:``, and never contain a
pytest summary token (``<digits> passed|failed|error``), so a gate that parses pytest's summary
can neither be satisfied nor tripped by the wrapper. The module deliberately does not import
pytest: pytest is a dev-group dependency, and the harness package ships to every install.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import FrameType
from typing import Final

# Nested compositors, in preference order. A second one is data, not code.
COMPOSITORS: Final = ("cage",)

# Removed from the compositor's environment. WAYLAND_DISPLAY / DISPLAY would make cage attach
# to the user's live session instead of building its own headless display; the KITTY_*
# variables would let a test's `kitten @` reach the user's running kitty.
SCRUBBED_VARIABLES: Final = (
    "WAYLAND_DISPLAY",
    "WAYLAND_SOCKET",
    "DISPLAY",
    "KITTY_LISTEN_ON",
    "KITTY_WINDOW_ID",
    "KITTY_PID",
    "KITTY_PUBLIC_KEY",
    # pytest prepends it to its argv unchecked, so PYTEST_ARGS is the one way options reach pytest.
    "PYTEST_ADDOPTS",
)

# Set for the compositor and, through it, for the child. KITTI_INTEGRATION=1 is set here and
# only here, so the integration items run inside the compositor and nowhere else.
HEADLESS_VARIABLES: Final[Mapping[str, str]] = {
    "WLR_BACKENDS": "headless",
    "WLR_LIBINPUT_NO_DEVICES": "1",
    "KITTI_INTEGRATION": "1",
}

INTEGRATION_ROOT: Final = Path("tests/integration")
COMPOSITOR_LOG: Final = Path("tmp/test-integration/compositor.log")

# The runner's own exit codes, all outside pytest's 0-5 range so a reader can tell a runner
# failure from a test failure (sysexits.h: EX_USAGE, EX_UNAVAILABLE, EX_SOFTWARE).
EXIT_USAGE: Final = 64
EXIT_UNAVAILABLE: Final = 69
EXIT_RUNNER_FAILURE: Final = 70

RUN_TIMEOUT_S: Final = 600.0
LEFTOVER_GRACE_S: Final = 5.0

# pytest 9.0.3 with pytest-cov 7.1.0: the option strings that take a value, as argparse reads each
# action's nargs (tmp/h43-runner-selectors/nargs.out, bypass.out). 55 take a mandatory value; the 3
# in _OPTIONAL_VALUE_OPTIONS take one only when the next argument does not start with "-".
_VALUE_OPTIONS: Final = frozenset(
    [
        "--assert",
        "--basetemp",
        "--capture",
        "--code-highlight",
        "--color",
        "--confcutdir",
        "--config-file",
        "--cov-config",
        "--cov-context",
        "--cov-fail-under",
        "--cov-precision",
        "--cov-report",
        "--deselect",
        "--doctest-glob",
        "--doctest-report",
        "--durations",
        "--durations-min",
        "--ignore",
        "--ignore-glob",
        "--import-mode",
        "--junit-prefix",
        "--junit-xml",
        "--junitprefix",
        "--junitxml",
        "--last-failed-no-failures",
        "--lfnf",
        "--log-auto-indent",
        "--log-cli-date-format",
        "--log-cli-format",
        "--log-cli-level",
        "--log-date-format",
        "--log-disable",
        "--log-file",
        "--log-file-date-format",
        "--log-file-format",
        "--log-file-level",
        "--log-file-mode",
        "--log-format",
        "--log-level",
        "--maxfail",
        "--override-ini",
        "--pastebin",
        "--pdbcls",
        "--pythonwarnings",
        "--rootdir",
        "--show-capture",
        "--tb",
        "--verbosity",
        "-W",
        "-c",
        "-k",
        "-m",
        "-o",
        "-p",
        "-r",
    ]
)
_OPTIONAL_VALUE_OPTIONS: Final = frozenset({"--cache-show", "--cov", "--debug"})
# Options that stop pytest loading tests/conftest.py (the collection hook), measured through
# tmp/h43-runner-selectors/bypass.out. `-o`/`--override-ini` are bypasses only with addopts.
_CONFTEST_BYPASS_OPTIONS: Final = frozenset({"--noconftest", "--confcutdir", "-c", "--config-file"})

_MODULE: Final = "kitty_setup.harness.integration_runner"
_CHILD_FLAG: Final = "--child"
_PREFIX: Final = "test-integration:"
_TERMINATING_SIGNALS: Final = (signal.SIGTERM, signal.SIGHUP)
_SIGTERM_GRACE_S: Final = 2.0
_POLL_S: Final = 0.05
_LOG_TAIL_LINES: Final = 20


class UsageError(ValueError):
    """``PYTEST_ARGS`` asked for something this runner refuses to run."""


class RunnerTerminatedError(Exception):
    """The runner received a terminating signal; raised so ``finally`` cleanup runs."""

    def __init__(self, signum: int) -> None:
        super().__init__(f"terminated by signal {signum}")
        self.signum = signum


class _CompositorGroup:
    """The compositor's process group: probe it, wait for it to empty, terminate it."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._process = process
        # start_new_session=True makes the compositor its own session and group leader.
        self._pgid = process.pid

    def is_empty(self) -> bool:
        # Reap the leader first: an unreaped leader is a zombie that still counts as a member.
        self._process.poll()
        try:
            os.killpg(self._pgid, 0)
        except ProcessLookupError:
            return True
        return False

    def wait_empty(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while not self.is_empty():
            if time.monotonic() >= deadline:
                return False
            time.sleep(_POLL_S)
        return True

    def terminate(self) -> bool:
        """SIGTERM, then SIGKILL, whatever is left. True when anything had to be signalled."""
        if self.is_empty():
            return False
        for signum in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(self._pgid, signum)
            except ProcessLookupError:
                break
            if self.wait_empty(_SIGTERM_GRACE_S):
                break
        self._process.poll()
        return True


def _say(message: str) -> None:
    print(f"{_PREFIX} {message}", file=sys.stderr, flush=True)


def _report_log(log_path: Path) -> None:
    _say(f"compositor log: {log_path}")
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines[-_LOG_TAIL_LINES:]:
        _say(f"| {line}")


def _read_status(status_path: Path) -> int | None:
    try:
        return int(status_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _raise_terminated(signum: int, frame: FrameType | None) -> None:
    del frame
    raise RunnerTerminatedError(signum)


def resolve_compositor() -> Path | None:
    """Return the absolute path of the first nested compositor on ``PATH``, or ``None``."""
    for name in COMPOSITORS:
        found = shutil.which(name)
        if found is not None:
            return Path(found).absolute()
    return None


def _split_options(arg: str) -> list[tuple[str, str | None]]:
    """The option strings one argument carries, each with its glued value, as argparse reads them.

    ``--name=value`` is ``--name`` with a value. A single-dash token is a cluster read left to
    right: a value option takes the rest of the token (one ``=`` right after it is not part of
    the value), or the next argument when nothing is left. Any other argument carries no option.
    """
    if arg.startswith("--"):
        name, equals, value = arg.partition("=")
        return [(name, value if equals else None)]
    if len(arg) < 2 or not arg.startswith("-"):
        return []
    found: list[tuple[str, str | None]] = []
    for position in range(1, len(arg)):
        option = "-" + arg[position]
        if option in _VALUE_OPTIONS:
            rest = arg[position + 1 :]
            found.append((option, rest[1:] if rest.startswith("=") else rest or None))
            break
        found.append((option, None))
    return found


def _refuse_bypass(option: str, value: str | None) -> None:
    """Refuse an option that would stop pytest loading tests/conftest.py, in any spelling."""
    addopts = (
        option in {"-o", "--override-ini"}
        and value is not None
        and value.split("=", 1)[0] == "addopts"
    )
    if option in _CONFTEST_BYPASS_OPTIONS or addopts:
        raise UsageError(
            f"{option!r} would stop pytest loading tests/conftest.py, whose collection hook keeps "
            "the run inside tests/integration/ — PYTEST_ARGS may only narrow the run"
        )


def build_pytest_args(argv: Sequence[str], *, cwd: Path | None = None) -> list[str]:
    """Turn ``PYTEST_ARGS`` into pytest's argv; never widen the run past ``tests/integration``.

    An argument is a path selector when it names an existing path (after stripping any
    ``::node`` suffix), and it is never a value that an option before it takes. Every selector
    must resolve inside ``INTEGRATION_ROOT``; with none, ``INTEGRATION_ROOT`` is prepended so a
    bare ``-k`` never reaches the unit tree. Any argument file, ``--child``, or option that could
    stop pytest loading ``tests/conftest.py`` is refused before the run starts.
    """
    base = Path.cwd() if cwd is None else cwd
    root = (base / INTEGRATION_ROOT).resolve()
    has_selector = False
    pending: str | None = None
    for arg in argv:
        if arg.startswith("@"):
            raise UsageError(
                f"{arg!r} is a pytest argument file, whose options could stop pytest loading "
                "tests/conftest.py, whose collection hook keeps the run inside tests/integration/ "
                "— PYTEST_ARGS may only narrow the run"
            )
        if arg == _CHILD_FLAG:
            raise UsageError(
                f"{arg!r} is the runner's own child entry point, never a pytest option — "
                "PYTEST_ARGS may only narrow the run"
            )
        if pending is not None:
            option, pending = pending, None
            if option in _VALUE_OPTIONS or not arg.startswith("-"):
                _refuse_bypass(option, arg)
                continue
        found = _split_options(arg)
        for option, value in found:
            _refuse_bypass(option, value)
        if found:
            option, value = found[-1]
            if value is None and (option in _VALUE_OPTIONS or option in _OPTIONAL_VALUE_OPTIONS):
                pending = option
            continue
        if not arg:
            continue
        candidate = base / arg.split("::", 1)[0]
        if not candidate.exists():
            continue
        if not candidate.resolve().is_relative_to(root):
            raise UsageError(
                f"{arg!r} is outside {INTEGRATION_ROOT.as_posix()}/ — PYTEST_ARGS may only "
                "select integration tests; the unit tree runs under `make test`"
            )
        has_selector = True
    return list(argv) if has_selector else [INTEGRATION_ROOT.as_posix(), *argv]


def headless_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of ``environ`` scrubbed of the live session and set up for headless."""
    env = {key: value for key, value in environ.items() if key not in SCRUBBED_VARIABLES}
    env.update(HEADLESS_VARIABLES)
    return env


def run(
    compositor: Path,
    pytest_args: Sequence[str],
    *,
    cwd: Path,
    environ: Mapping[str, str],
    timeout_s: float = RUN_TIMEOUT_S,
    grace_s: float = LEFTOVER_GRACE_S,
) -> int:
    """Run pytest inside ``compositor`` and return pytest's own status, or a runner failure."""
    log_path = cwd / COMPOSITOR_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        tempfile.TemporaryDirectory(prefix="kitti-integration-") as scratch,
        log_path.open("wb") as log,
    ):
        status_path = Path(scratch) / "pytest-status"
        argv = [
            str(compositor),
            "--",
            sys.executable,
            "-c",
            _CHILD_PROGRAM,
            str(status_path),
            "--",
            *pytest_args,
        ]
        process = subprocess.Popen(
            argv,
            env=headless_env(environ),
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stderr=log,
            start_new_session=True,
        )
        group = _CompositorGroup(process)
        try:
            try:
                compositor_status = process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                group.terminate()
                _say(
                    f"FAILED — the run hit its {timeout_s:g}-second timeout; the compositor's "
                    "process group was killed and pytest's verdict is unknown."
                )
                _report_log(log_path)
                return EXIT_RUNNER_FAILURE
            leftover = not group.wait_empty(grace_s) and group.terminate()
        finally:
            group.terminate()
        status = _read_status(status_path)

    if leftover:
        pytest_part = "" if status is None else f" (pytest exit status {status})"
        _say(
            f"FAILED — processes were left behind in the compositor's process group {grace_s:g}s "
            f"after it exited; they were terminated{pytest_part}. A run that leaves processes "
            "behind is not a pass."
        )
        return EXIT_RUNNER_FAILURE
    if status is None:
        _say(
            "FAILED — the child's status file is missing, so pytest's verdict is unknown "
            f"(compositor exited {compositor_status}). This is a failure, not a pass."
        )
        _report_log(log_path)
        return EXIT_RUNNER_FAILURE
    if status < 0:
        _say(
            f"FAILED — pytest was killed by signal {-status} "
            f"(compositor exited {compositor_status})."
        )
        return EXIT_RUNNER_FAILURE
    _say(
        f"pytest exit status {status} (read from the child's status file; "
        f"compositor exited {compositor_status})"
    )
    return status


def _child(args: Sequence[str]) -> int:
    """Inside the compositor: run pytest, write its status to the status file, return it."""
    if len(args) < 2 or args[1] != "--":
        _say("usage error — child entry: <status-file> -- <pytest args>")
        return EXIT_USAGE
    status_path = Path(args[0])
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *args[2:]], stderr=subprocess.STDOUT, check=False
    )
    status_path.write_text(f"{completed.returncode}\n", encoding="utf-8")
    return completed.returncode


# The child's only entry point: `run()` starts it as `python -c`, and no PYTEST_ARGS reach it,
# because `main` never calls `_child` and `build_pytest_args` refuses `--child`.
_CHILD_PROGRAM: Final = (
    f"import sys; from {_MODULE} import {_child.__name__}; "
    f"raise SystemExit({_child.__name__}(sys.argv[1:]))"
)


def main(argv: Sequence[str]) -> int:
    cwd = Path.cwd()
    try:
        pytest_args = build_pytest_args(list(argv), cwd=cwd)
    except UsageError as exc:
        _say(f"usage error — {exc}")
        return EXIT_USAGE

    compositor = resolve_compositor()
    if compositor is None:
        _say(
            f"FAILED — no nested compositor found (looked for: {', '.join(COMPOSITORS)}). "
            "The integration suite was NOT run; this is a failure, not a skip."
        )
        _say("To fix: install cage, or run on a host that has a nested compositor.")
        return EXIT_UNAVAILABLE

    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "")
    if not runtime_dir or not Path(runtime_dir).is_dir():
        problem = "is unset" if not runtime_dir else f"is not a directory ({runtime_dir})"
        _say(
            f"FAILED — XDG_RUNTIME_DIR {problem}; the compositor needs it for its Wayland "
            "socket. The integration suite was NOT run; this is a failure, not a skip."
        )
        return EXIT_UNAVAILABLE

    previous = {signum: signal.signal(signum, _raise_terminated) for signum in _TERMINATING_SIGNALS}
    try:
        return run(compositor, pytest_args, cwd=cwd, environ=os.environ)
    except RunnerTerminatedError as exc:
        _say(
            f"FAILED — the runner was terminated by signal {exc.signum}; the compositor's "
            "process group was killed and pytest's verdict is unknown."
        )
        return 128 + exc.signum
    finally:
        for signum, handler in previous.items():
            if handler is not None:
                signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
