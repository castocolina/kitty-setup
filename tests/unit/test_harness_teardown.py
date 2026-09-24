"""Pin: the harness teardown verb stays ``close-window`` (U-1, D-13 as amended 2026-09-23).

Read this before "fixing" the teardown. D-13's original wording said the harness should issue
``close-os-window`` instead of ``close-window``. That was measured and **dropped**. It was not
deferred.

The measurement, on kitty 0.49.0 (02-RESEARCH §U-1, re-run headless by plan 02-08 in
``tmp/h32-color-forms/u1-live-before.txt``):

* ``close-os-window`` is not a ``kitten @`` subcommand. ``kitten @ --help`` lists 41
  subcommands, including ``close-tab`` and ``close-window``, and no ``close-os-window``. That
  name exists only as a mappable action (``close_os_window``). Called, it exits 1 with
  ``Error: close-os-window is not a known subcommand for @.``
* ``close-window --match=all`` against a kitty with 2 OS windows and 3 windows exits 0, and kitty
  exits cleanly (socket gone, process exit code 0). After ``close-os-window --match=all`` on the
  same setup, kitty is still running with both OS windows.

Why the wrong verb would be **silent**. ``_close_window_then_terminate`` wraps the remote-control
call in ``except HarnessCommandError: pass``. With ``close-os-window`` the error is swallowed and
kitty keeps running. Teardown then waits out the close grace, sends SIGTERM, and maybe SIGKILL,
on every integration test. Nothing turns red. The only symptom is integration wall-clock time
rising with no failures (02-RESEARCH Pitfall 3).

What is pinned here: the verb and its ``--match=all``, the absence of ``close-os-window`` from the
harness, and the non-propagation of ``HarnessCommandError``. That last property is what makes a
wrong verb invisible, so it is pinned as well as described. Plan ``02-09`` rewrites the
``try/except/pass`` into ``contextlib.suppress`` (ruff SIM105). That rewrite changes neither the
verb nor the non-propagation, and these tests must stay green through it.

No kitty is needed. The session is constructed but not entered, so nothing is spawned and no
socket directory is created. The binaries are fake paths. ``_kctl`` is replaced by a recorder, and
with ``_process`` unset the method returns right after the remote-control call. Private names are
reached by string (``monkeypatch.setattr`` and ``vars(type(session))``) so the module stays
pyright-strict clean.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kitty_setup.harness import kitty_session
from kitty_setup.harness.kitty_session import HarnessCommandError, KittyBinaries, KittySession

_FAKE_BINARIES = KittyBinaries(kitty=Path("/nonexistent/kitty"), kitten=Path("/nonexistent/kitten"))
_TEARDOWN = "_close_window_then_terminate"


def _unentered_session(tmp_path: Path) -> KittySession:
    return KittySession(cwd=tmp_path, binaries=_FAKE_BINARIES)


def _teardown(session: KittySession) -> None:
    vars(type(session))[_TEARDOWN](session)


def test_teardown_issues_close_window_match_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one remote-control call teardown makes is ``close-window --match=all``."""
    session = _unentered_session(tmp_path)
    calls: list[tuple[str, ...]] = []

    def record(sub: str, *args: str, _retry_on_failure: bool = True) -> str:
        del _retry_on_failure
        calls.append((sub, *args))
        return ""

    monkeypatch.setattr(session, "_kctl", record)
    _teardown(session)
    assert calls == [("close-window", "--match=all")]


def test_teardown_never_uses_close_os_window() -> None:
    """``close-os-window`` is not a ``kitten @`` subcommand on kitty 0.49.0; it appears nowhere."""
    source = Path(kitty_session.__file__).read_text(encoding="utf-8")
    assert '"close-window", "--match=all"' in source
    assert "close-os-window" not in source
    assert "close_os_window" not in source


def test_teardown_swallows_harness_command_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing verb does not propagate. This is exactly why a wrong verb would go unseen."""
    session = _unentered_session(tmp_path)
    calls: list[str] = []

    def fail(sub: str, *args: str, _retry_on_failure: bool = True) -> str:
        del _retry_on_failure
        calls.append(sub)
        raise HarnessCommandError(
            f"kitten @ {sub} {' '.join(args)} → exit 1: Error: {sub} is not a known subcommand"
        )

    monkeypatch.setattr(session, "_kctl", fail)
    _teardown(session)
    assert calls == ["close-window"]
