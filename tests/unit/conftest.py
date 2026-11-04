"""Autouse host-effect guard for the unit tree (02-12 IN-08).

A tripwire for the test's own process, not a sandbox. While a unit test runs, an audit hook sees
what CPython audits here and aborts the operation before it happens, then the fixture fails the
test at teardown, so code under test that swallows the abort is still caught. It guards:

- an exec of a program under a footprint root, in each event's own context: a ``Popen``
  program joined to its ``cwd`` and resolved through its PATH, an ``os.exec`` path joined to the
  cwd with no PATH search, and an ``os.posix_spawn`` path both ways;
- a write, mkdir, rename, removal, symlink or chmod under a root, a ``dir_fd`` read through
  ``/proc/self/fd``, and an ``open`` for writing;
- a socket connect off loopback, and a name lookup off loopback (``getaddrinfo``,
  ``gethostbyname``, ``gethostbyaddr`` and ``getnameinfo``).

Roots are the kitty-setup footprint under the real HOME, ``$XDG_CONFIG_HOME/kitty-setup`` and
``$XDG_RUNTIME_DIR`` where set at import. ``/tmp`` and ``tmp_path`` are never roots. Each root and
each event path is compared in every prefix form (see ``_forms``), so a symlinked file inside a
directory root, an intermediate directory symlink and a HOME alias are all caught.

What the guard cannot see (T-2-55): a child process's own effects after its exec, a C extension's
own syscalls, and ``ctypes``. A child that can reach the footprint is held at the subprocess
boundary instead, by the committed child-env AST rule in ``test_unit_hermeticity.py``. The guard
holds no allow-list of spawning modules: a later plan that adds a child-spawning unit module needs
no edit here, and records the child in its own SUMMARY (program, env source, why it cannot reach
the footprint).
"""

from __future__ import annotations

import ipaddress
import os
import sys
from collections.abc import Iterator, Sequence
from typing import cast

import pytest

_FOOTPRINT: tuple[str, ...] = (
    ".local/bin/kitty",
    ".local/bin/kitten",
    ".local/bin/my-kitty",
    ".local/bin/my-kitty-setup",
    ".local/kitty.app",
    ".local/share/kitty-setup",
    ".local/share/applications",
    ".config/kitty",
    ".config/kitty-setup",
    ".bashrc",
    ".zshrc",
)
_MUTATIONS: frozenset[str] = frozenset(
    {"os.mkdir", "os.rename", "os.remove", "os.rmdir", "os.symlink", "os.chmod", "shutil.rmtree"}
)
_LOOKUPS: frozenset[str] = frozenset(
    {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr", "socket.getnameinfo"}
)


class HostStateReachedError(BaseException):
    """Raised by the guard in place of a host effect.

    A ``BaseException``, so an ``except Exception`` in the code under test cannot swallow it.
    """


def _forms(path: str) -> tuple[str, ...]:
    """Every prefix form of an absolute ``path``.

    For each k from 0 to the number of components, the first k components are resolved with
    ``os.path.realpath`` and the rest are appended unresolved; the result is normalised. k = 0 is
    the lexical form, k = n the fully resolved one. Duplicates are dropped.
    """
    comps = [c for c in path.split("/") if c not in ("", ".")]
    seen: dict[str, None] = {}
    for k in range(len(comps) + 1):
        head = os.path.realpath("/" + "/".join(comps[:k])) if k else "/"
        seen.setdefault(os.path.normpath(os.path.join(head, *comps[k:])), None)
    return tuple(seen)


_REAL_HOME: str = os.path.realpath(os.path.expanduser("~"))
_ROOT_PATHS: list[str] = [os.path.join(_REAL_HOME, rel) for rel in _FOOTPRINT]
if os.environ.get("XDG_CONFIG_HOME"):
    _ROOT_PATHS.append(os.path.join(os.environ["XDG_CONFIG_HOME"], "kitty-setup"))
if os.environ.get("XDG_RUNTIME_DIR"):
    _ROOT_PATHS.append(os.environ["XDG_RUNTIME_DIR"])
_ROOT_FORMS: tuple[str, ...] = tuple(dict.fromkeys(f for r in _ROOT_PATHS for f in _forms(r)))

_ACTIVE: list[list[str]] = []
_BUSY: list[bool] = [False]


def _under(forms: tuple[str, ...], roots: tuple[str, ...]) -> bool:
    return any(f == r or f.startswith(r.rstrip("/") + "/") for f in forms for r in roots)


def _as_text(raw: object) -> str | None:
    """An event's path or host as text: str or bytes, or a PathLike."""
    if isinstance(raw, bytes):
        return os.fsdecode(raw)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, os.PathLike):
        return os.fsdecode(os.fspath(cast("os.PathLike[str] | os.PathLike[bytes]", raw)))
    return None


def _items(value: object) -> Sequence[object] | None:
    """The elements of a list or tuple event argument, or None for anything else."""
    if isinstance(value, (list, tuple)):
        return cast("Sequence[object]", value)
    return None


def _getcwd() -> str | None:
    try:
        return os.getcwd()
    except OSError:
        return None


def _context(dir_fd: object) -> str | None:
    """The directory a relative path is joined to: the ``dir_fd``'s target, else the cwd.

    None when that context cannot be read, so the caller fails closed.
    """
    if isinstance(dir_fd, int) and dir_fd >= 0:
        try:
            target = os.readlink(f"/proc/self/fd/{dir_fd}")
        except OSError:
            return None
        if not os.path.isabs(target) or target.endswith(" (deleted)"):
            return None
        return target
    return _getcwd()


def _place(raw: object, dir_fd: object) -> str | None:
    text = _as_text(raw)
    if text is None:
        return None
    if os.path.isabs(text):
        return text
    base = _context(dir_fd)
    return None if base is None else os.path.join(base, text)


def _exec_base(cwd: object) -> str | None:
    if cwd is None:
        return _getcwd()
    text = _as_text(cwd)
    if text is None:
        return None
    if os.path.isabs(text):
        return text
    base = _getcwd()
    return None if base is None else os.path.join(base, text)


def _is_executable(candidate: str) -> bool:
    return os.path.isfile(candidate) and os.access(candidate, os.X_OK)


def _exec_hit(event: str, candidate: str) -> str | None:
    if _under(_forms(candidate), _ROOT_FORMS):
        return f"{event} {candidate}"
    return None


def _popen_program(executable: object, argv: object) -> object:
    if executable is not None:
        return executable
    items = _items(argv)
    if items:
        return items[0]
    return argv


def _check_popen(args: tuple[object, ...]) -> str | None:
    """``subprocess.Popen``: (executable, args, cwd, env). A slash is joined to the cwd; a bare
    name is searched on the child's PATH, relative entries joined to the same cwd."""
    executable, argv, cwd, env = args[0], args[1], args[2], args[3]
    program = _popen_program(executable, argv)
    text = _as_text(program)
    base = _exec_base(cwd)
    if text is None or base is None:
        return f"subprocess.Popen: path context unresolved ({program!r})"
    if "/" in text:
        candidate = text if os.path.isabs(text) else os.path.join(base, text)
        return _exec_hit("subprocess.Popen", candidate)
    env_map: dict[str, str] | None = None
    if isinstance(env, dict):
        env_map = {str(k): str(v) for k, v in cast("dict[object, object]", env).items()}
    for entry in os.get_exec_path(env_map):
        directory = entry if os.path.isabs(entry) else os.path.join(base, entry)
        candidate = os.path.join(directory, text)
        if _is_executable(candidate):
            return _exec_hit("subprocess.Popen", candidate)
    return None


def _check_exec(args: tuple[object, ...]) -> str | None:
    """``os.exec*``: the path the kernel runs. Relative to the cwd; PATH is never searched."""
    text = _as_text(args[0])
    cwd = _getcwd()
    if text is None or cwd is None:
        return f"os.exec: path context unresolved ({args[0]!r})"
    candidate = text if os.path.isabs(text) else os.path.join(cwd, text)
    return _exec_hit("os.exec", candidate)


def _check_spawn(args: tuple[object, ...]) -> str | None:
    """``os.posix_spawn`` and ``os.posix_spawnp`` raise the same event, so both are checked: the
    path against the cwd, and for a bare name the first executable on the process's PATH."""
    text = _as_text(args[0])
    cwd = _getcwd()
    if text is None or cwd is None:
        return f"os.posix_spawn: path context unresolved ({args[0]!r})"
    if os.path.isabs(text):
        return _exec_hit("os.posix_spawn", text)
    hit = _exec_hit("os.posix_spawn", os.path.join(cwd, text))
    if hit is not None or "/" in text:
        return hit
    for entry in os.get_exec_path():
        directory = entry if os.path.isabs(entry) else os.path.join(cwd, entry)
        candidate = os.path.join(directory, text)
        if _is_executable(candidate):
            return _exec_hit("os.posix_spawn", candidate)
    return None


def _opens_for_writing(mode: object, flags: object) -> bool:
    if isinstance(mode, str):
        return any(c in mode for c in "wax+")
    if isinstance(flags, int):
        return bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
    return False


def _check_open(args: tuple[object, ...]) -> str | None:
    """``open`` (mode is a string) and ``os.open`` (mode is None, and no dir_fd is audited)."""
    raw, mode, flags = args[0], args[1], args[2]
    if isinstance(raw, int) or not _opens_for_writing(mode, flags):
        return None
    text = _as_text(raw)
    if text is None:
        return f"open: path context unresolved ({raw!r})"
    if os.path.isabs(text):
        placed: str | None = text
    elif mode is None:
        return f"open {text!r}: path context unresolved (os.open, dir_fd not audited)"
    else:
        placed = _place(text, None)
    if placed is None:
        return f"open {text!r}: path context unresolved"
    if _under(_forms(placed), _ROOT_FORMS):
        return f"open {placed} for writing"
    return None


def _check_mutation(event: str, args: tuple[object, ...]) -> str | None:
    """Each mutation's path arguments and their dir_fd, per the event's audit shape."""
    targets: list[tuple[object, object]]
    if event == "os.rename":
        targets = [(args[0], args[2]), (args[1], args[3])]
    elif event == "os.symlink":
        targets = [(args[1], args[2])]
    elif event == "shutil.rmtree":
        targets = [(args[0], None)]
    else:
        targets = [(args[0], args[-1])]
    for raw, dir_fd in targets:
        if isinstance(raw, int):
            continue
        placed = _place(raw, dir_fd)
        if placed is None:
            return f"{event}: path context unresolved ({raw!r})"
        if _under(_forms(placed), _ROOT_FORMS):
            return f"{event} {placed}"
    return None


def _loopback(host: object) -> bool:
    if host is None:
        return True
    text = _as_text(host)
    if text is None:
        return False
    if text == "localhost":
        return True
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


def _check_connect(args: tuple[object, ...]) -> str | None:
    address = args[1]
    items = _items(address)
    if items:
        if not _loopback(items[0]):
            return f"socket.connect {items[0]!r}: non-loopback host"
        return None
    if isinstance(address, (str, bytes)):
        placed = _place(address, None)
        if placed is None or _under(_forms(placed), _ROOT_FORMS):
            return f"socket.connect {address!r}: path under a root or unresolved"
    return None


def _check_lookup(event: str, args: tuple[object, ...]) -> str | None:
    """Name lookups. ``getnameinfo`` takes a sockaddr, so its host is ``args[0][0]``."""
    if event == "socket.getnameinfo":
        sockaddr = _items(args[0])
        host: object = sockaddr[0] if sockaddr else None
    else:
        host = args[0]
    if _loopback(host):
        return None
    return f"{event} {host!r}: non-loopback lookup"


def _check(event: str, args: tuple[object, ...]) -> str | None:
    try:
        if event == "subprocess.Popen":
            return _check_popen(args)
        if event == "os.exec":
            return _check_exec(args)
        if event == "os.posix_spawn":
            return _check_spawn(args)
        if event == "open":
            return _check_open(args)
        if event in _MUTATIONS:
            return _check_mutation(event, args)
        if event == "socket.connect":
            return _check_connect(args)
        if event in _LOOKUPS:
            return _check_lookup(event, args)
    except (IndexError, TypeError, ValueError) as exc:
        return f"{event}: unreadable event arguments ({type(exc).__name__})"
    return None


def _hook(event: str, args: tuple[object, ...]) -> None:
    """The audit hook. It returns at once when re-entered, so its own calls cannot recurse."""
    if not _ACTIVE or _BUSY[0]:
        return
    _BUSY[0] = True
    try:
        hit = _check(event, args)
    finally:
        _BUSY[0] = False
    if hit is not None:
        _ACTIVE[-1].append(hit)
        raise HostStateReachedError(f"host state reached: {hit}")


sys.addaudithook(_hook)


@pytest.fixture(autouse=True)
def hermetic_guard() -> Iterator[None]:
    """Arm the guard for one test; fail the test at teardown if any host effect was reached."""
    hits: list[str] = []
    _ACTIVE.append(hits)
    try:
        yield
    finally:
        _ACTIVE.pop()
    if hits:
        pytest.fail("host state reached: " + "; ".join(hits), pytrace=False)
