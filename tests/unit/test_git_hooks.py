"""Regression tests for the tracked git hooks under ``tools/hooks/``.

Covers all three tracked hooks: the ``pre-push`` policy guard (R0.4) and the two
CodeGraph lifecycle hooks ``post-checkout`` and ``post-commit`` (R0.6).

Materialises a disposable git sandbox per test inside pytest's ``tmp_path``: a
bare ``remote.git`` plus a ``clone`` whose ``core.hooksPath`` is ``tools/hooks``
and whose ``tools/hooks/`` is a mode-preserving ``shutil.copytree`` of this
repo's **tracked** hook directory. The tests therefore exercise the real hook
files, never a fixture re-implementation; ``copytree`` uses ``copy2``, which
preserves the 0755 bit git requires before it will execute a hook.

The CodeGraph cases never invoke the real ``codegraph`` binary. They put a
purpose-built shim first on a **copied** ``PATH`` for the one git call under
test — a recording shim that logs its argv and cwd, a shim that fails, and a
shim that sleeps far past the hook's timeout budget — or, for the
absent-binary cases, a ``PATH`` holding nothing but symlinks to the externals
the hooks actually need. ``os.environ`` is never mutated.

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
import time
from collections.abc import Generator, Mapping
from pathlib import Path
from typing import Final

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR: Final[Path] = REPO_ROOT / "tools" / "hooks"
GIT_BUDGET_S: Final[float] = 30.0
SEED_FILE: Final[str] = "seed.txt"
HOOK_TAG: Final[str] = "[pre-push]"
CHECKOUT_TAG: Final[str] = "[post-checkout]"
COMMIT_TAG: Final[str] = "[post-commit]"
#: Every warning path in both CodeGraph hooks begins its message with this word,
#: which is what R0.6's "must warn, never abort" half is asserted against.
WARNING_WORD: Final[str] = "warning"
#: Read by the recording shim below; set per-test, never exported process-wide.
SHIM_LOG_ENV: Final[str] = "KITTI_SHIM_LOG"
#: The hooks' overridable timeout budget, in seconds.
TIMEOUT_ENV: Final[str] = "KITTI_CODEGRAPH_TIMEOUT_S"
#: Budget for the hang case: the hook must return within this many seconds even
#: though the shim sleeps for ``_SLEEP_S``. Generous enough not to be flaky, far
#: below ``GIT_BUDGET_S`` and far below ``_SLEEP_S``, so a broken timeout cannot
#: pass by accident.
HANG_BUDGET_S: Final[float] = 15.0

#: Appends ``<argv>\t<cwd>`` for every invocation. The cwd matters as much as the
#: argv: git runs ``post-checkout`` with cwd set to the **newly created**
#: worktree, and an index built anywhere else is the wrong index.
_RECORDING_SHIM: Final[str] = """printf '%s\\t%s\\n' "$*" "$PWD" >> "${KITTI_SHIM_LOG}"
exit 0
"""
_FAILING_SHIM: Final[str] = """printf 'shim: deliberate codegraph failure\\n' >&2
exit 1
"""
#: Seconds the sleeping shim sleeps — orders of magnitude past the 1-second
#: budget the hang test sets.
_SLEEP_S: Final[int] = 120
#: ``exec`` makes ``sleep`` the direct child of ``timeout`` so the kill cannot be
#: deferred behind a bash ``wait``, and the redirections stop an orphan from
#: holding the captured hook pipes open.
_SLEEPING_SHIM: Final[str] = f"exec sleep {_SLEEP_S} >/dev/null 2>&1 </dev/null\n"
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


def _tagged(result: subprocess.CompletedProcess[str], tag: str) -> str:
    """Return every line the hook prefixed with ``tag``, across both streams.

    Scoped to the hook's own tag so an assertion cannot be satisfied by git's
    wording. Both streams are searched because which one git forwards where is
    not worth depending on.
    """
    lines = result.stdout.splitlines() + result.stderr.splitlines()
    return "\n".join(line for line in lines if line.startswith(tag))


def _hook_output(result: subprocess.CompletedProcess[str]) -> str:
    """Return every ``[pre-push]`` line the hook emitted, across both streams."""
    return _tagged(result, HOOK_TAG)


def _shim_dir(tmp_path: Path, name: str, body: str) -> Path:
    """Create a directory holding one executable ``name`` running ``body``; return the directory.

    The returned directory is meant to be pushed onto the **front** of a copied
    ``PATH`` for a single git call, so the hook under test resolves ``name`` to
    the shim instead of the real binary.
    """
    shim_bin = tmp_path / "shim-bin"
    shim_bin.mkdir(exist_ok=True)
    shim = shim_bin / name
    shim.write_text(f"#!/usr/bin/env bash\n{body}", encoding="utf-8")
    shim.chmod(0o755)
    return shim_bin


def _minimal_path(tmp_path: Path) -> Path:
    """Return a directory of symlinks to the only externals the hooks can need.

    Used as the **sole** ``PATH`` entry for the absent-binary cases, so
    ``command -v codegraph`` genuinely fails instead of finding a shim. ``bash``
    because both hooks' shebang is ``/usr/bin/env bash``, ``git`` for the
    operation itself, and ``dirname`` because the house ``REPO_ROOT`` idiom calls
    it — the CodeGraph hooks deliberately do not use that idiom (they must stay in
    the cwd git handed them), but the symlink is kept so this helper stays valid
    for any hook that does.
    """
    minimal = tmp_path / "minimal-path"
    minimal.mkdir(exist_ok=True)
    for tool in ("git", "bash", "dirname"):
        resolved = shutil.which(tool)
        if resolved is None:
            pytest.skip(
                f"{tool} does not resolve on PATH; the absent-codegraph case cannot be built"
            )
        link = minimal / tool
        if not link.exists():
            link.symlink_to(resolved)
    return minimal


def _path_env(
    *entries: Path,
    prepend: bool = True,
    overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return an env copy whose ``PATH`` is ``entries``, plus the real one when ``prepend``.

    ``overrides`` is an explicit mapping rather than ``**overrides: str``: the env-var
    names callers need are module constants, so every call site had to spell the keywords
    as ``**{CONST: value}``, and unpacking a ``dict[str, str]`` into a signature carrying
    the keyword-only ``prepend: bool`` makes a type checker report the ``str`` value as a
    candidate for ``prepend`` (four ``reportArgumentType`` errors, measured). A mapping
    parameter expresses the same thing with no ambiguity to resolve.
    """
    parts = [str(entry) for entry in entries]
    if prepend:
        parts.append(os.environ.get("PATH", ""))
    env = _push_env(PATH=os.pathsep.join(parts))
    if overrides:
        env.update(overrides)
    return env


def _shim_rows(log: Path) -> list[tuple[str, str]]:
    """Return the recording shim's ``(argv, cwd)`` rows, or ``[]`` if it never ran."""
    if not log.exists():
        return []
    rows: list[tuple[str, str]] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        argv, _, cwd = line.partition("\t")
        rows.append((argv, cwd))
    return rows


def _argvs(rows: list[tuple[str, str]]) -> list[str]:
    """Return just the recorded argv strings, for exact-match assertions."""
    return [argv for argv, _ in rows]


def _cwds_for(rows: list[tuple[str, str]], argv: str) -> list[Path]:
    """Return the resolved cwds of every invocation whose argv matched ``argv`` exactly."""
    return [Path(cwd).resolve() for recorded, cwd in rows if recorded == argv]


def _commit(clone: Path, text: str, message: str) -> None:
    """Rewrite the seed file and commit it, so every commit carries a real tree change."""
    (clone / SEED_FILE).write_text(text, encoding="utf-8")
    _check(_git("add", SEED_FILE, cwd=clone), f"git add ({message})")
    _check(_git("commit", "-m", message, cwd=clone), f"git commit ({message})")


@contextlib.contextmanager
def _sandbox(
    tmp_path: Path, *, push_master: bool = True
) -> Generator[tuple[Path, Path], None, None]:
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


# --------------------------------------------------------------------------- #
# post-checkout — the CodeGraph index lifecycle on worktree creation (R0.6)
# --------------------------------------------------------------------------- #


def _worktree_add(
    clone: Path, target: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Create a new worktree at ``target`` on a fresh branch, under ``env``."""
    return _git("worktree", "add", str(target), "-b", "wt-codegraph", cwd=clone, env=env)


def test_post_checkout_indexes_new_worktree(tmp_path: Path) -> None:
    """A brand-new worktree triggers exactly ``codegraph init -y``, in the new worktree's cwd."""
    shim_log = tmp_path / "shim.log"
    shim = _shim_dir(tmp_path, "codegraph", _RECORDING_SHIM)
    worktree = tmp_path / "wt"
    with _sandbox(tmp_path) as (_remote, clone):
        result = _worktree_add(
            clone, worktree, _path_env(shim, overrides={SHIM_LOG_ENV: str(shim_log)})
        )

    assert result.returncode == 0, f"worktree add failed:\n{result.stderr}"
    rows = _shim_rows(shim_log)
    # Exact argv, not just the first word: a hook calling bare `codegraph init`
    # would hang on a prompt in a fresh worktree, and must not pass this test.
    assert "init -y" in _argvs(rows), (
        "the hook did not run `codegraph init -y`; recorded invocations were: "
        f"{_argvs(rows) or '(none at all)'}"
    )
    # git runs post-checkout with cwd set to the NEW worktree, but resolves the
    # hook FILE from the invoking worktree. A hook that cd'd to its own repo root
    # would index the wrong tree, so the cwd is asserted, not assumed.
    assert _cwds_for(rows, "init -y") == [worktree.resolve()], (
        "`codegraph init -y` did not run inside the new worktree; it ran in: "
        f"{_cwds_for(rows, 'init -y')}"
    )
    announced = _tagged(result, CHECKOUT_TAG)
    assert announced, f"no {CHECKOUT_TAG} line at all:\n{result.stdout}\n{result.stderr}"
    assert WARNING_WORD not in announced, f"the success path warned:\n{announced}"
    assert "index" in announced, f"the success line does not name the index:\n{announced}"


def test_post_checkout_ignores_ordinary_branch_switch(tmp_path: Path) -> None:
    """An ordinary same-worktree branch switch rebuilds nothing.

    The distinguishing signal is the previous-HEAD argument: git passes the
    all-zero SHA only on a first checkout (a new worktree or clone); an ordinary
    switch passes a real commit.
    """
    shim_log = tmp_path / "shim.log"
    shim = _shim_dir(tmp_path, "codegraph", _RECORDING_SHIM)
    env = _path_env(shim, overrides={SHIM_LOG_ENV: str(shim_log)})
    with _sandbox(tmp_path) as (_remote, clone):
        _check(_git("checkout", "-b", "other", cwd=clone, env=env), "git checkout -b other")
        _check(_git("checkout", "master", cwd=clone, env=env), "git checkout master")

    initialised = [argv for argv in _argvs(_shim_rows(shim_log)) if argv.startswith("init")]
    assert not initialised, "an ordinary branch switch triggered an index build: " f"{initialised}"


def test_post_checkout_codegraph_failure_leaves_worktree_intact(tmp_path: Path) -> None:
    """A failing codegraph leaves the new worktree usable and prints a tagged warning."""
    shim = _shim_dir(tmp_path, "codegraph", _FAILING_SHIM)
    worktree = tmp_path / "wt"
    with _sandbox(tmp_path) as (_remote, clone):
        result = _worktree_add(clone, worktree, _path_env(shim))

    assert result.returncode == 0, f"a codegraph failure aborted the checkout:\n{result.stderr}"
    assert (worktree / SEED_FILE).read_text(
        encoding="utf-8"
    ) == "seed\n", f"the new worktree does not hold the checked-out seed file: {worktree}"
    announced = _tagged(result, CHECKOUT_TAG)
    assert announced, f"no {CHECKOUT_TAG} line at all:\n{result.stdout}\n{result.stderr}"
    assert (
        WARNING_WORD in announced
    ), f"R0.6 requires a warning on the failure path; the hook said:\n{announced}"


def test_post_checkout_codegraph_absent_leaves_worktree_intact(tmp_path: Path) -> None:
    """An absent codegraph leaves the new worktree usable and prints a tagged warning."""
    worktree = tmp_path / "wt"
    minimal = _minimal_path(tmp_path)
    with _sandbox(tmp_path) as (_remote, clone):
        result = _worktree_add(clone, worktree, _path_env(minimal, prepend=False))

    assert result.returncode == 0, f"an absent codegraph aborted the checkout:\n{result.stderr}"
    assert (worktree / SEED_FILE).read_text(
        encoding="utf-8"
    ) == "seed\n", f"the new worktree does not hold the checked-out seed file: {worktree}"
    announced = _tagged(result, CHECKOUT_TAG)
    assert announced, f"no {CHECKOUT_TAG} line at all:\n{result.stdout}\n{result.stderr}"
    assert (
        WARNING_WORD in announced
    ), f"R0.6 requires a warning when the binary is absent; the hook said:\n{announced}"


# --------------------------------------------------------------------------- #
# post-commit — the incremental CodeGraph refresh (R0.6, D-13)
# --------------------------------------------------------------------------- #


def _head(clone: Path) -> str:
    """Return the clone's current HEAD sha."""
    return _check(_git("rev-parse", "HEAD", cwd=clone), "git rev-parse HEAD").stdout.strip()


def _stage(clone: Path, text: str) -> None:
    """Write and stage a real tree change, so the following commit is a genuine commit."""
    (clone / SEED_FILE).write_text(text, encoding="utf-8")
    _check(_git("add", SEED_FILE, cwd=clone), "git add (post-commit case)")


def test_post_commit_syncs_index(tmp_path: Path) -> None:
    """A commit triggers exactly ``codegraph sync -q``, in the committing worktree."""
    shim_log = tmp_path / "shim.log"
    shim = _shim_dir(tmp_path, "codegraph", _RECORDING_SHIM)
    with _sandbox(tmp_path) as (_remote, clone):
        _stage(clone, "synced\n")
        result = _git(
            "commit",
            "-m",
            "a commit that should refresh the index",
            cwd=clone,
            env=_path_env(shim, overrides={SHIM_LOG_ENV: str(shim_log)}),
        )
        clone_root = clone.resolve()

    assert result.returncode == 0, f"the commit failed:\n{result.stderr}"
    rows = _shim_rows(shim_log)
    # Exact argv: a bare `codegraph sync` would lose the quiet flag the hook
    # depends on, and D-13 names `sync`, not the full `index` rebuild.
    assert "sync -q" in _argvs(rows), (
        "the hook did not run `codegraph sync -q`; recorded invocations were: "
        f"{_argvs(rows) or '(none at all)'}"
    )
    assert _cwds_for(rows, "sync -q") == [
        clone_root
    ], f"`codegraph sync -q` did not run in the committing worktree: {_cwds_for(rows, 'sync -q')}"
    announced = _tagged(result, COMMIT_TAG)
    assert announced, f"no {COMMIT_TAG} line at all:\n{result.stdout}\n{result.stderr}"
    assert WARNING_WORD not in announced, f"the success path warned:\n{announced}"
    assert "index" in announced, f"the success line does not name the index:\n{announced}"


def test_post_commit_codegraph_failure_does_not_block_commit(tmp_path: Path) -> None:
    """A failing codegraph cannot fail a commit, and says so with a tagged warning."""
    shim = _shim_dir(tmp_path, "codegraph", _FAILING_SHIM)
    with _sandbox(tmp_path) as (_remote, clone):
        before = _head(clone)
        _stage(clone, "failing shim\n")
        result = _git(
            "commit", "-m", "commit with a failing codegraph", cwd=clone, env=_path_env(shim)
        )
        after = _head(clone)

    assert result.returncode == 0, f"a codegraph failure blocked the commit:\n{result.stderr}"
    assert after != before, "HEAD did not advance, so the commit did not happen"
    announced = _tagged(result, COMMIT_TAG)
    assert announced, f"no {COMMIT_TAG} line at all:\n{result.stdout}\n{result.stderr}"
    assert (
        WARNING_WORD in announced
    ), f"R0.6 requires a warning on the failure path; the hook said:\n{announced}"


def test_post_commit_codegraph_absent_does_not_block_commit(tmp_path: Path) -> None:
    """An absent codegraph cannot fail a commit, and says so with a tagged warning."""
    minimal = _minimal_path(tmp_path)
    with _sandbox(tmp_path) as (_remote, clone):
        before = _head(clone)
        _stage(clone, "no codegraph at all\n")
        result = _git(
            "commit",
            "-m",
            "commit with no codegraph on PATH",
            cwd=clone,
            env=_path_env(minimal, prepend=False),
        )
        after = _head(clone)

    assert result.returncode == 0, f"an absent codegraph blocked the commit:\n{result.stderr}"
    assert after != before, "HEAD did not advance, so the commit did not happen"
    announced = _tagged(result, COMMIT_TAG)
    assert announced, f"no {COMMIT_TAG} line at all:\n{result.stdout}\n{result.stderr}"
    assert (
        WARNING_WORD in announced
    ), f"R0.6 requires a warning when the binary is absent; the hook said:\n{announced}"


def test_post_commit_codegraph_hang_does_not_block_commit(tmp_path: Path) -> None:
    """A codegraph that never returns cannot block a commit — the timeout bounds it.

    Skipped, loudly, on a host with no ``timeout`` binary: there the mitigation is
    genuinely unavailable rather than broken, and that is a fact to report, not to
    paper over with a green test.
    """
    if shutil.which("timeout") is None:
        pytest.skip(
            "no `timeout` binary on this host: the hang mitigation is unavailable, not broken"
        )
    shim = _shim_dir(tmp_path, "codegraph", _SLEEPING_SHIM)
    with _sandbox(tmp_path) as (_remote, clone):
        before = _head(clone)
        _stage(clone, "hanging shim\n")
        started = time.monotonic()
        result = _git(
            "commit",
            "-m",
            "commit with a codegraph that never returns",
            cwd=clone,
            env=_path_env(shim, overrides={TIMEOUT_ENV: "1"}),
        )
        elapsed = time.monotonic() - started
        after = _head(clone)

    assert result.returncode == 0, f"a hanging codegraph blocked the commit:\n{result.stderr}"
    assert after != before, "HEAD did not advance, so the commit did not happen"
    assert elapsed < HANG_BUDGET_S, (
        f"the commit took {elapsed:.1f}s against a {TIMEOUT_ENV}=1 budget, "
        f"so the {_SLEEP_S}s shim was not bounded"
    )
    announced = _tagged(result, COMMIT_TAG)
    assert announced, f"no {COMMIT_TAG} line at all:\n{result.stdout}\n{result.stderr}"
    assert (
        WARNING_WORD in announced
    ), f"R0.6 requires a warning when the call times out; the hook said:\n{announced}"
