"""Regression tests for the tracked git hooks under ``tools/hooks/``.

Materialises a disposable git sandbox per test inside pytest's ``tmp_path``: a
bare ``remote.git`` plus a ``clone`` whose ``core.hooksPath`` is ``tools/hooks``
and whose ``tools/hooks/`` is a mode-preserving ``shutil.copytree`` of this
repo's **tracked** hook directory. The tests therefore exercise the real hook
files, never a fixture re-implementation; ``copytree`` uses ``copy2``, which
preserves the 0755 bit git requires before it will execute a hook.

Uses pytest's ``tmp_path`` fixture rather than the stdlib temp-directory
context manager: ``TemporaryDirectory`` has zero occurrences anywhere under
``tests/``, so ``tmp_path`` is the house fixture (and pytest retains the last
few runs' directories, which is strictly better for post-mortem of a failed
push).

Lives under ``tests/unit/`` and deliberately **not** under
``tests/integration/``: the path gate in ``tests/conftest.py`` (lines 44-53)
skips everything in the integration tree unless ``KITTI_INTEGRATION=1``, so a
verify command aimed there reports green while executing nothing. These tests
need only ``git`` — no kitty, no ``KITTI_INTEGRATION`` semantics — so they
belong in the ungated tree where ``make test`` actually runs them.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Final

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR: Final[Path] = REPO_ROOT / "tools" / "hooks"
GIT_BUDGET_S: Final[float] = 30.0
SEED_FILE: Final[str] = "seed.txt"
HOOK_TAG: Final[str] = "[pre-push]"
#: The pre-push guard's own escape hatch. The sandbox bootstrap uses it for its
#: very first ``master`` push, because that push is a deliberate repo bootstrap
#: against an empty remote ref, which the provenance guard rejects by design
#: (see the hook header's limits block, item 6).
ALLOW_MASTER: Final[str] = "KITTI_ALLOW_MASTER_PUSH"


def _git(
    *args: str, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``git`` with a fixed argv list in ``cwd`` and return the completed process."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=dict(os.environ) if env is None else env,
        capture_output=True,
        text=True,
        check=False,
        timeout=GIT_BUDGET_S,
    )


def _check(result: subprocess.CompletedProcess[str], what: str) -> subprocess.CompletedProcess[str]:
    """Assert a sandbox-setup git command succeeded, surfacing its output when it did not."""
    assert result.returncode == 0, f"{what} failed ({result.returncode}):\n{result.stderr}"
    return result


def _push_env(**overrides: str) -> dict[str, str]:
    """Return a copy of the process environment with ``overrides`` applied."""
    env = dict(os.environ)
    env.update(overrides)
    return env


def _rejections(result: subprocess.CompletedProcess[str]) -> list[str]:
    """Return the hook's own tagged diagnostic lines from a push's stderr.

    Scoped to lines the hook itself emitted so an assertion cannot be satisfied
    by git's own wording (git prints its own "non-fast-forward" hint on a
    rejected push, which would otherwise make a broken guard read as working).
    """
    return [line for line in result.stderr.splitlines() if line.startswith(HOOK_TAG)]


def _hook_output(result: subprocess.CompletedProcess[str]) -> str:
    """Return every ``[pre-push]`` line the hook emitted, across both streams.

    The hook's ``log`` helper writes to stdout and its ``err`` helper to stderr;
    which stream git forwards where is not worth depending on for a non-rejection
    announcement, so announcements are matched across both.
    """
    lines = result.stdout.splitlines() + result.stderr.splitlines()
    return "\n".join(line for line in lines if line.startswith(HOOK_TAG))


def _commit(clone: Path, text: str, message: str) -> None:
    """Rewrite the seed file and commit it, so every commit carries a real tree change."""
    (clone / SEED_FILE).write_text(text, encoding="utf-8")
    _check(_git("add", SEED_FILE, cwd=clone), f"git add ({message})")
    _check(_git("commit", "-m", message, cwd=clone), f"git commit ({message})")


@contextlib.contextmanager
def _sandbox(tmp_path: Path, *, push_master: bool = True) -> Iterator[tuple[Path, Path]]:
    """Yield ``(remote, clone)`` for a disposable repo pair wired to the tracked hooks.

    ``push_master=False`` leaves ``refs/heads/master`` absent on the remote, which
    is the state the first-push-of-master edge case needs.
    """
    remote = tmp_path / "remote.git"
    clone = tmp_path / "clone"
    _check(_git("init", "--bare", str(remote), cwd=tmp_path), "git init --bare")
    clone.mkdir()
    _check(_git("init", "-b", "master", str(clone), cwd=tmp_path), "git init clone")
    for key, value in (
        ("user.email", "sandbox@example.invalid"),
        ("user.name", "Sandbox Agent"),
        ("commit.gpgsign", "false"),
    ):
        _check(_git("config", key, value, cwd=clone), f"git config {key}")
    shutil.copytree(HOOKS_DIR, clone / "tools" / "hooks")
    _check(_git("config", "core.hooksPath", "tools/hooks", cwd=clone), "git config core.hooksPath")
    _commit(clone, "seed\n", "seed")
    _check(_git("remote", "add", "origin", str(remote), cwd=clone), "git remote add")
    if push_master:
        _check(
            _git(
                "push",
                "-u",
                "origin",
                "master",
                cwd=clone,
                env=_push_env(**{ALLOW_MASTER: "1"}),
            ),
            "bootstrap git push master",
        )
    yield remote, clone


def test_force_push_rejected(tmp_path: Path) -> None:
    """A rewrite of an already-pushed ref is rejected, naming the rewrite guard."""
    with _sandbox(tmp_path) as (_remote, clone):
        # A tracked-file change before the amend, so the amended commit is a genuinely
        # different object: a bare `--amend --no-edit` with no tree change can reproduce
        # the same commit id within timestamp resolution and pass for the wrong reason.
        (clone / SEED_FILE).write_text("amended\n", encoding="utf-8")
        _check(_git("add", SEED_FILE, cwd=clone), "git add (amend)")
        _check(_git("commit", "--amend", "--no-edit", cwd=clone), "git commit --amend")
        result = _git("push", "--force", "origin", "master", cwd=clone)

    assert result.returncode != 0, f"force push was not rejected:\n{result.stderr}"
    rejections = _rejections(result)
    assert rejections, f"no {HOOK_TAG} diagnostic on stderr:\n{result.stderr}"
    joined = "\n".join(rejections)
    assert any(
        "non-fast-forward" in line for line in rejections
    ), f"rejection does not name the rewrite guard:\n{joined}"


def test_fast_forward_push_allowed(tmp_path: Path) -> None:
    """A second, fast-forward push of a phase branch is allowed with no rejection."""
    with _sandbox(tmp_path) as (_remote, clone):
        _check(_git("checkout", "-b", "gsd/phase-9-sandbox", cwd=clone), "git checkout -b")
        _commit(clone, "first\n", "first on phase branch")
        _check(
            _git("push", "-u", "origin", "gsd/phase-9-sandbox", cwd=clone),
            "first phase-branch push",
        )
        _commit(clone, "second\n", "second on phase branch")
        result = _git("push", "origin", "gsd/phase-9-sandbox", cwd=clone)

    assert result.returncode == 0, f"fast-forward push was rejected:\n{result.stderr}"
    assert not _rejections(result), f"unexpected {HOOK_TAG} diagnostic:\n{result.stderr}"


def test_new_branch_push_allowed(tmp_path: Path) -> None:
    """A brand-new non-master ref (all-zero remote_sha) is allowed with no rejection."""
    with _sandbox(tmp_path) as (_remote, clone):
        _check(_git("checkout", "-b", "gsd/phase-8-sandbox", cwd=clone), "git checkout -b")
        _commit(clone, "only\n", "only commit on new phase branch")
        result = _git("push", "-u", "origin", "gsd/phase-8-sandbox", cwd=clone)

    assert result.returncode == 0, f"new-branch push was rejected:\n{result.stderr}"
    assert not _rejections(result), f"unexpected {HOOK_TAG} diagnostic:\n{result.stderr}"


def _merge_branch_to_master_push(tmp_path: Path, branch: str) -> subprocess.CompletedProcess[str]:
    """Commit on ``branch``, merge it into master with --no-ff, and push master."""
    with _sandbox(tmp_path) as (_remote, clone):
        _check(_git("checkout", "-b", branch, cwd=clone), f"git checkout -b {branch}")
        _commit(clone, f"work on {branch}\n", f"work on {branch}")
        _check(_git("checkout", "master", cwd=clone), "git checkout master")
        _check(
            _git("merge", "--no-ff", "-m", f"merge {branch}", branch, cwd=clone),
            f"git merge --no-ff {branch}",
        )
        return _git("push", "origin", "master", cwd=clone)


def test_direct_commit_to_master_rejected(tmp_path: Path) -> None:
    """A commit authored directly on master is rejected, naming the provenance guard."""
    with _sandbox(tmp_path) as (_remote, clone):
        _commit(clone, "direct\n", "authored straight onto master")
        result = _git("push", "origin", "master", cwd=clone)

    assert result.returncode != 0, f"direct-to-master push was not rejected:\n{result.stderr}"
    rejections = _rejections(result)
    assert rejections, f"no {HOOK_TAG} diagnostic on stderr:\n{result.stderr}"
    joined = "\n".join(rejections)
    assert any(
        "provenance" in line for line in rejections
    ), f"rejection does not name the provenance guard:\n{joined}"


def test_phase_branch_merge_to_master_allowed(tmp_path: Path) -> None:
    """A --no-ff merge of a gsd/phase-* branch into master is allowed."""
    result = _merge_branch_to_master_push(tmp_path, "gsd/phase-7-sandbox")

    assert result.returncode == 0, f"phase-branch merge was rejected:\n{result.stderr}"
    assert not _rejections(result), f"unexpected {HOOK_TAG} diagnostic:\n{result.stderr}"


def test_milestone_branch_merge_to_master_allowed(tmp_path: Path) -> None:
    """A gsd/{milestone}-{slug} merge is allowed — the negative control for the gsd/* glob.

    ``.planning/config.json`` sets ``git.milestone_branch_template`` to
    ``gsd/{milestone}-{slug}``, which a narrower ``gsd/phase-*`` glob would reject.
    """
    result = _merge_branch_to_master_push(tmp_path, "gsd/v1-remediation")

    assert result.returncode == 0, f"milestone-branch merge was rejected:\n{result.stderr}"
    assert not _rejections(result), f"unexpected {HOOK_TAG} diagnostic:\n{result.stderr}"


def test_master_escape_hatch_allows_direct_push(tmp_path: Path) -> None:
    """KITTI_ALLOW_MASTER_PUSH=1 skips the provenance guard and says so out loud."""
    with _sandbox(tmp_path) as (_remote, clone):
        _commit(clone, "direct with hatch\n", "authored straight onto master")
        result = _git("push", "origin", "master", cwd=clone, env=_push_env(**{ALLOW_MASTER: "1"}))

    assert result.returncode == 0, f"escape hatch did not allow the push:\n{result.stderr}"
    announced = _hook_output(result)
    assert ALLOW_MASTER in announced, (
        "the hook did not announce that the escape hatch was honoured; "
        f"its output was:\n{announced or '(no [pre-push] lines at all)'}"
    )


def test_first_push_of_master_to_empty_remote_rejected(tmp_path: Path) -> None:
    """The first-ever push of master (all-zero remote_sha) is rejected, not waved through.

    With no remote tip there is no range to enumerate, so the hook cannot establish
    provenance and must not pretend it did.
    """
    with _sandbox(tmp_path, push_master=False) as (_remote, clone):
        result = _git("push", "-u", "origin", "master", cwd=clone)

    assert result.returncode != 0, f"first push of master was not rejected:\n{result.stderr}"
    rejections = _rejections(result)
    assert rejections, f"no {HOOK_TAG} diagnostic on stderr:\n{result.stderr}"
    joined = "\n".join(rejections)
    assert any(
        "provenance" in line for line in rejections
    ), f"rejection does not name the provenance guard:\n{joined}"
    assert ALLOW_MASTER in result.stderr, (
        "the rejection does not name the sanctioned route for a deliberate bootstrap:\n"
        f"{result.stderr}"
    )


def test_master_deletion_rejected(tmp_path: Path) -> None:
    """Deleting refs/heads/master on the remote is rejected."""
    with _sandbox(tmp_path) as (_remote, clone):
        result = _git("push", "origin", ":master", cwd=clone)

    assert result.returncode != 0, f"master deletion was not rejected:\n{result.stderr}"
    assert _rejections(result), f"no {HOOK_TAG} diagnostic on stderr:\n{result.stderr}"


def test_phase_branch_deletion_allowed(tmp_path: Path) -> None:
    """Deleting a merged phase branch stays routine — the negative control for the rule."""
    with _sandbox(tmp_path) as (_remote, clone):
        _check(_git("checkout", "-b", "gsd/phase-6-sandbox", cwd=clone), "git checkout -b")
        _commit(clone, "disposable\n", "work on a disposable phase branch")
        _check(
            _git("push", "-u", "origin", "gsd/phase-6-sandbox", cwd=clone),
            "phase-branch push",
        )
        _check(_git("checkout", "master", cwd=clone), "git checkout master")
        result = _git("push", "origin", ":gsd/phase-6-sandbox", cwd=clone)

    assert result.returncode == 0, f"phase-branch deletion was rejected:\n{result.stderr}"
    assert not _rejections(result), f"unexpected {HOOK_TAG} diagnostic:\n{result.stderr}"
