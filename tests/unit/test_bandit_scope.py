"""Per-site bandit fence and the ``urllib.request`` import fence (IN-05 / A-3, 02-15).

``pyproject.toml``'s ``[tool.bandit] skips`` is global: bandit's TOML config cannot scope an id
to a file, so B604 (``shell=``) and B607 (partial executable path) are kept in ``skips`` and this
module fences them per site instead. A site is ``(file, id, enclosing def, callee)``, so a
same-file swap of an allowed call for a planted one changes a key even when every per-(file, id)
count stays equal. ``make test`` runs this module, which makes it the merge gate for the
canonical ``uv run bandit -c pyproject.toml -q -r src`` that R0.11 pins. B310 is no longer
fenced: its only site, the ``urlopen`` in the installer download, is gone (IN-06).
"""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path
from typing import Final, cast

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
NARROW_IDS: Final[tuple[str, ...]] = ("B310", "B604", "B607")

SiteKey = tuple[str, str, str, str]

# Bandit's per-site keys over src/ at HEAD after 02-14, from tmp/h45-bandit-scope/rerun.txt.
# The installer.py B604 key moved when 02-14 rewrote the completion path.
SITE_ALLOWLIST: Final[Counter[SiteKey]] = Counter(
    {
        (
            "src/kitty_setup/installer.py",
            "B604",
            "generate_completion_script",
            "_ARGCOMPLETE_SHELLCODE",
        ): 1,
        ("src/kitty_setup/installer.py", "B607", "_run_upstream_installer", "subprocess.run"): 1,
        (
            "src/kitty_setup/path_integration.py",
            "B604",
            "ensure_local_bin_in_path",
            "PathEditResult",
        ): 7,
        ("src/kitty_setup/scenes/_client.py", "B607", "pgrep_kitty_pids", "subprocess.run"): 1,
    }
)


def _scope_of(tree: ast.AST, call: ast.Call) -> str:
    """The dotted qualname of the def or class around ``call``, or ``<module>``."""

    def visit(node: ast.AST, scope: tuple[str, ...]) -> str | None:
        for child in ast.iter_child_nodes(node):
            if child is call:
                return ".".join(scope) or "<module>"
            name = (
                child.name
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                else None
            )
            found = visit(child, (*scope, name) if name else scope)
            if found is not None:
                return found
        return None

    result = visit(tree, ())
    assert result is not None, "the call is not in its own tree"
    return result


def _sites(root: Path) -> Counter[SiteKey]:
    """Bandit's B310/B604/B607 findings over ``root/src``, one key per finding's own call."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "bandit",
            "-q",
            "-r",
            "src",
            "-t",
            ",".join(NARROW_IDS),
            "-f",
            "json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode in (0, 1), proc.stderr
    report = cast(dict[str, object], json.loads(proc.stdout))
    assert report["errors"] == [], report["errors"]
    sites: Counter[SiteKey] = Counter()
    for finding in cast(list[dict[str, object]], report["results"]):
        # Bandit reports the path it was given, relative to the run's cwd (root), as `src/...`.
        relative = Path(str(finding["filename"])).as_posix()
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        line = min(cast(list[int], finding["line_range"]))
        col = cast(int, finding["col_offset"])
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and node.lineno == line and node.col_offset == col
        ]
        assert len(calls) == 1, f"{relative}:{line} maps to {len(calls)} calls, not one"
        call = calls[0]
        key = (
            relative,
            str(finding["test_id"]),
            _scope_of(tree, call),
            ast.unparse(call.func),
        )
        sites[key] += 1
    return sites


def _per_file_id(sites: Counter[SiteKey]) -> Counter[tuple[str, str]]:
    totals: Counter[tuple[str, str]] = Counter()
    for (path, test_id, _scope, _callee), count in sites.items():
        totals[(path, test_id)] += count
    return totals


def test_bandit_narrow_ids_match_the_site_allowlist() -> None:
    found = _sites(REPO_ROOT)
    beyond = found - SITE_ALLOWLIST
    missing = SITE_ALLOWLIST - found
    assert (
        found == SITE_ALLOWLIST
    ), f"sites beyond the allowlist: {dict(beyond)}; missing: {dict(missing)}"


def test_bandit_skips_keep_only_the_scoped_ids() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    skips = cast(list[str], data["tool"]["bandit"]["skips"])
    assert skips == ["B404", "B603", "B604", "B607"]


def test_bandit_fence_sees_a_replaced_site(tmp_path: Path) -> None:
    """Negative control: a same-file swap keeps each per-(file, id) count and changes a site key."""
    shutil.copytree(REPO_ROOT / "src", tmp_path / "src")
    before = _sites(tmp_path)
    key = next(k for k in before if k[1] == "B604" and k[0].endswith("installer.py"))
    installer_path = tmp_path / key[0]
    text = installer_path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    target = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _scope_of(tree, node) == key[2]
        and ast.unparse(node.func) == key[3]
    )
    segment = ast.get_source_segment(text, target)
    assert segment is not None
    installer_path.write_text(
        text.replace(segment, '_planted("echo hi", shell=True)', 1), encoding="utf-8"
    )

    after = _sites(tmp_path)

    assert _per_file_id(after) == _per_file_id(before), "the per-(file, id) fence would pass"
    assert after != before, "the per-site fence must see the replaced call"
    assert any(k[3] == "_planted" for k in after)


def test_network_fetch_lives_only_in_installer() -> None:
    """Only ``installer.py`` imports ``urllib.request``, so a second fetch cannot hide from B310's
    successor, the per-site fence above (T-2-70)."""
    importers: set[str] = set()
    for path in sorted((REPO_ROOT / "src" / "kitty_setup").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name == "urllib.request" for a in node.names):
                importers.add(path.relative_to(REPO_ROOT).as_posix())
            if isinstance(node, ast.ImportFrom) and (
                node.module == "urllib.request"
                or (node.module == "urllib" and any(a.name == "request" for a in node.names))
            ):
                importers.add(path.relative_to(REPO_ROOT).as_posix())
    assert importers == {"src/kitty_setup/installer.py"}, importers
