"""Autonomous, isolated Kitty sessions for hypothesis-driven verification.

Implements the kitty-test-harness capability. ``KittySession`` is a context
manager that:

1. Spawns Kitty with a per-session Unix socket and a per-session config dir
   under ``tmp/sessions/<id>/``.
2. Polls the socket up to 5 seconds for readiness.
3. Exposes ``ls()`` / ``send_key()`` / ``send_text()`` / ``launch()`` /
   ``get_text()`` wrappers around ``kitten @ --to unix:<sock>``.
4. Closes the OS window cleanly on exit, then SIGTERM and finally SIGKILL the
   process if it lingers. Wipes its session directory on success unless
   ``KEEP_SESSIONS=1`` is set.

The harness ignores the user's ``~/.config/kitty/`` because every session
points ``--config`` at its own session-local file.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import shutil
import signal
import subprocess
import time
import uuid
from pathlib import Path
from types import TracebackType
from typing import Any, Final

DEFAULT_SOCKET_BUDGET_S: Final[float] = 5.0
DEFAULT_CLOSE_GRACE_S: Final[float] = 2.0
DEFAULT_KILL_GRACE_S: Final[float] = 5.0


class HarnessStartupError(RuntimeError):
    """Raised when a Kitty session never becomes ready on its socket."""


class HarnessCommandError(RuntimeError):
    """Raised when a ``kitten @`` call returns non-zero."""


@dataclasses.dataclass(frozen=True, slots=True)
class KittyBinaries:
    """Resolved paths to the Kitty CLI tools used by the harness."""

    kitty: Path
    kitten: Path

    @classmethod
    def discover(cls) -> KittyBinaries:
        """Locate Kitty/kitten via ``$PATH`` first, then the standard install prefix."""
        candidates = [
            Path.home() / ".local" / "kitty.app" / "bin",
            Path.home() / ".local" / "bin",
        ]
        kitty_on_path = shutil.which("kitty")
        kitten_on_path = shutil.which("kitten")
        kitty: Path | None = Path(kitty_on_path) if kitty_on_path else None
        kitten: Path | None = Path(kitten_on_path) if kitten_on_path else None
        for prefix in candidates:
            if kitty is None and (prefix / "kitty").is_file():
                kitty = prefix / "kitty"
            if kitten is None and (prefix / "kitten").is_file():
                kitten = prefix / "kitten"
        if kitty is None or kitten is None:
            raise HarnessStartupError(
                "kitty / kitten not found on PATH or under ~/.local/kitty.app/bin"
            )
        return cls(kitty=kitty, kitten=kitten)


def _sessions_root() -> Path:
    """Return ``<repo>/tmp/sessions`` (created on demand). Always absolute."""
    repo_root = Path(__file__).resolve().parents[3]
    root = repo_root / "tmp" / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


_ANSI_RE: Final[re.Pattern[str]] = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


class KittySession:
    """Context manager wrapping an isolated Kitty process driven by ``kitten @``."""

    def __init__(
        self,
        *,
        cwd: Path | None = None,
        config_snippets: list[str] | None = None,
        binaries: KittyBinaries | None = None,
        socket_budget_s: float = DEFAULT_SOCKET_BUDGET_S,
        close_grace_s: float = DEFAULT_CLOSE_GRACE_S,
        kill_grace_s: float = DEFAULT_KILL_GRACE_S,
    ) -> None:
        self._binaries = binaries or KittyBinaries.discover()
        self._cwd = (cwd or Path.cwd()).resolve()
        self._config_snippets = list(config_snippets or [])
        self._socket_budget_s = socket_budget_s
        self._close_grace_s = close_grace_s
        self._kill_grace_s = kill_grace_s
        self._session_id: str = ""
        self._session_dir: Path = Path()
        self._socket_path: Path = Path()
        self._config_path: Path = Path()
        self._log_path: Path = Path()
        self._process: subprocess.Popen[bytes] | None = None

    # ---- public lifecycle -------------------------------------------------

    @property
    def socket_path(self) -> Path:
        return self._socket_path

    @property
    def session_dir(self) -> Path:
        return self._session_dir

    def __enter__(self) -> KittySession:
        self._session_id = f"s{uuid.uuid4().hex[:10]}"
        self._session_dir = _sessions_root() / self._session_id
        self._session_dir.mkdir(parents=True, exist_ok=False)
        (self._session_dir / "home").mkdir()
        self._socket_path = self._session_dir / "sock"
        self._config_path = self._session_dir / "kitty.conf"
        self._log_path = self._session_dir / "kitty.log"
        self._write_session_config()
        self._spawn_kitty()
        try:
            self._wait_for_socket()
        except HarnessStartupError:
            self._kill_process()
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if self._process is not None and self._process.poll() is None:
                self._close_window_then_terminate()
        finally:
            keep = exc is not None or os.environ.get("KEEP_SESSIONS") == "1"
            if not keep and self._session_dir.exists():
                shutil.rmtree(self._session_dir, ignore_errors=True)

    # ---- public method wrappers ------------------------------------------

    def ls(self) -> list[dict[str, Any]]:
        """Return ``kitten @ ls`` parsed as a list of OS-window dicts."""
        raw = self._kctl("ls")
        return json.loads(raw)

    def send_key(self, keys: str) -> None:
        """Send a key chord (e.g. ``"ctrl+shift+t"``) to the active window."""
        self._kctl("send-key", keys)

    def send_text(self, text: str) -> None:
        """Send literal text to the active window."""
        self._kctl("send-text", text)

    def launch(self, **kwargs: str) -> dict[str, Any] | None:
        """Run ``kitten @ launch`` with the given options. Returns parsed JSON if any."""
        args: list[str] = []
        for key, value in kwargs.items():
            flag = f"--{key.replace('_', '-')}"
            if value is True or value == "":
                args.append(flag)
            else:
                args.append(f"{flag}={value}")
        raw = self._kctl("launch", *args)
        raw = raw.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    def get_text(self, *, extent: str = "all") -> str:
        """Return the text of the active window, ANSI-stripped."""
        raw = self._kctl("get-text", f"--extent={extent}")
        return _strip_ansi(raw)

    def action(self, name: str, *args: str) -> None:
        """Invoke a kitty mappable action (the same actions referenced in keybindings)."""
        self._kctl("action", name, *args)

    # ---- internals --------------------------------------------------------

    def _write_session_config(self) -> None:
        # bash --noprofile --norc keeps the shell deterministic across hosts; the
        # default user shell (zsh, fish, etc.) may pop interactive wizards when
        # the session HOME is empty, which corrupts probe input.
        lines: list[str] = [
            "# kitty-setup harness session config — generated, do not edit.",
            "allow_remote_control yes",
            "shell bash --noprofile --norc",
            "",
            *self._config_snippets,
            "",
        ]
        self._config_path.write_text("\n".join(lines), encoding="utf-8")

    def _spawn_kitty(self) -> None:
        listen_on = f"unix:{self._socket_path}"
        argv = [
            str(self._binaries.kitty),
            "-o",
            "allow_remote_control=yes",
            f"--listen-on={listen_on}",
            f"--config={self._config_path}",
            f"--directory={self._cwd}",
            "--start-as=minimized",
        ]
        env = dict(os.environ)
        env["HOME"] = str(self._session_dir / "home")
        env.setdefault("XDG_RUNTIME_DIR", "/tmp")  # noqa: S108 — fall-back only when unset
        log = self._log_path.open("ab")
        try:
            self._process = subprocess.Popen(  # noqa: S603 — args constructed from trusted paths
                argv,
                stdout=log,
                stderr=log,
                env=env,
                cwd=str(self._cwd),
            )
        except FileNotFoundError as exc:
            log.close()
            raise HarnessStartupError(f"failed to spawn kitty: {exc}") from exc

    def _wait_for_socket(self) -> None:
        deadline = time.monotonic() + self._socket_budget_s
        last_error: str = "no attempt"
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise HarnessStartupError(
                    f"kitty exited early (code {self._process.returncode}); "
                    f"see {self._log_path}"
                )
            if self._socket_path.exists():
                try:
                    self._kctl("ls", _retry_on_failure=False)
                    return
                except HarnessCommandError as exc:
                    last_error = str(exc)
            time.sleep(0.05)
        raise HarnessStartupError(
            f"socket {self._socket_path} not ready within {self._socket_budget_s}s; "
            f"last error: {last_error}; log: {self._log_path}"
        )

    def _kctl(self, sub: str, *args: str, _retry_on_failure: bool = True) -> str:
        del _retry_on_failure  # reserved for future retry logic
        argv = [
            str(self._binaries.kitten),
            "@",
            f"--to=unix:{self._socket_path}",
            sub,
            *args,
        ]
        try:
            result = subprocess.run(  # noqa: S603 — args constructed from trusted paths
                argv,
                capture_output=True,
                check=False,
                timeout=15,
            )
        except FileNotFoundError as exc:
            raise HarnessCommandError(f"kitten not found: {exc}") from exc
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise HarnessCommandError(
                f"kitten @ {sub} {' '.join(args)} → exit {result.returncode}: {stderr}"
            )
        return result.stdout.decode("utf-8", errors="replace")

    def _close_window_then_terminate(self) -> None:
        try:
            self._kctl("close-window", "--match=all")
        except HarnessCommandError:
            pass  # process may already be tearing down
        if self._process is None:
            return
        try:
            self._process.wait(timeout=self._close_grace_s)
            return
        except subprocess.TimeoutExpired:
            self._process.send_signal(signal.SIGTERM)
        try:
            self._process.wait(timeout=self._kill_grace_s)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=2.0)

    def _kill_process(self) -> None:
        if self._process is None:
            return
        with self._process:
            try:
                self._process.kill()
            except ProcessLookupError:
                pass
