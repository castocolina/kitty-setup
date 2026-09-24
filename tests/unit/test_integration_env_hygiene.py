"""Static rule: an integration test that runs our own CLI must not leak ``KITTY_WINDOW_ID`` (R1.6).

Why the rule exists. ``KITTY_WINDOW_ID`` is read in exactly one place in ``src/``,
``launcher._origin_window``. When it is set, ``launch_scene`` fills the current tab
instead of opening a new one. kitty exports the variable into every window it runs. So an
integration test that copies ``os.environ`` and runs ``python -m kitty_setup.cli`` from inside a
kitty window hands the child the developer's window id. The child then takes the
fill-current-tab branch, and the test's new-tab assertions fail. The suite's verdict depends on
where it was launched from (D-10).

What the rule selects. A function in ``tests/integration/*.py`` is selected only when it builds
an env from ``dict(os.environ)`` or ``os.environ.copy()`` **and** passes that env as ``env=`` to a
``subprocess`` call whose argv contains the string ``kitty_setup.cli``, i.e. the child runs our
own CLI. An env builder that spawns ``kitty`` or ``kitten @`` directly is not selected. Neither
binary reads the variable for us, so those builders are harmless (02-RESEARCH A4). Every
selected function must call ``<env>.pop("KITTY_WINDOW_ID", ...)`` before that subprocess call.
A deliberate re-injection after the pop (``test_scene_recipe_e2e._run_scene_launch``
simulates a launch from inside kitty) is allowed.

The rule lives in ``tests/unit/`` on purpose. ``tests/conftest.py`` skips every item under
``tests/integration/`` unless ``KITTI_INTEGRATION=1``, so a rule placed there would report green
in a plain ``make test`` while running nothing. The integration tree is located from this
module's own ``__file__``, so the rule reads the checkout it sits in.
"""

from __future__ import annotations

import ast
import dataclasses
from collections.abc import Iterator
from pathlib import Path

INTEGRATION_DIR = Path(__file__).resolve().parents[1] / "integration"
OUR_CLI = "kitty_setup.cli"
WINDOW_ID = "KITTY_WINDOW_ID"
_SUBPROCESS_FUNCS = frozenset({"run", "Popen", "call", "check_call", "check_output"})

# The four env builders measured at 02-08 (by module and function) that run our own CLI.
KNOWN_CLI_BUILDERS = frozenset(
    {
        ("test_color_normalization_e2e.py", "_run"),
        (
            "test_scene_recipe_e2e.py",
            "test_my_kitty_scene_launch_named_recipe_creates_three_pane_tab",
        ),
        ("test_scene_recipe_e2e.py", "_run_scene_launch"),
        ("test_h25_scene_launcher.py", "test_my_kitty_scene_launch_cli_creates_three_pane_tab"),
    }
)
# Env builders measured at 02-08 that spawn ``kitty`` or ``kitten @`` directly (not selected).
KNOWN_SPAWNERS = frozenset(
    {
        ("_kitty_subprocess.py", "spawn_kitty"),
        ("_kitty_subprocess.py", "kitten_call"),
        ("test_client_socket_discovery.py", "_spawn_kitty"),
        ("test_h21_doctor_remote_control.py", "_spawn_kitty"),
        ("test_h21_remote_control_foundation.py", "_spawn_kitty"),
        ("test_h21_remote_control_foundation.py", "_kitten_ls"),
    }
)


@dataclasses.dataclass(frozen=True, slots=True)
class EnvBuilder:
    """One ``dict(os.environ)`` / ``os.environ.copy()`` env handed to a subprocess."""

    module: str
    function: str
    line: int
    runs_our_cli: bool
    pops_window_id: bool


def _own_nodes(func: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterator[ast.AST]:
    """Yield every node in ``func``'s body, not descending into nested defs or lambdas."""
    stack: list[ast.AST] = list(reversed(func.body))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
            continue
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def _is_os_environ(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _is_environ_copy(node: ast.AST | None) -> bool:
    """``dict(os.environ)`` or ``os.environ.copy()``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id == "dict":
        return len(node.args) == 1 and _is_os_environ(node.args[0])
    return isinstance(func, ast.Attribute) and func.attr == "copy" and _is_os_environ(func.value)


def _is_subprocess_call(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in _SUBPROCESS_FUNCS
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def _mentions_our_cli(expr: ast.AST, assigned: dict[str, list[ast.AST]]) -> bool:
    """True if a string constant inside ``expr`` names our CLI module.

    A bare name used as the argv is resolved through its assignments in the same function.
    """
    roots: list[ast.AST] = [expr]
    if isinstance(expr, ast.Name):
        roots.extend(assigned.get(expr.id, []))
    for root in roots:
        for node in ast.walk(root):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and OUR_CLI in node.value
            ):
                return True
    return False


def _argv_of(call: ast.Call) -> ast.AST | None:
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg == "args":
            return kw.value
    return None


def _env_name_of(call: ast.Call) -> str | None:
    for kw in call.keywords:
        if kw.arg == "env" and isinstance(kw.value, ast.Name):
            return kw.value.id
    return None


def _pop_lines(nodes: list[ast.AST], env: str) -> list[int]:
    """Lines of ``<env>.pop("KITTY_WINDOW_ID", ...)`` calls."""
    lines: list[int] = []
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "pop"
            and isinstance(func.value, ast.Name)
            and func.value.id == env
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == WINDOW_ID
        ):
            lines.append(node.lineno)
    return lines


def classify_source(source: str, module: str) -> list[EnvBuilder]:
    """Every env builder in ``source`` that feeds a subprocess, with the rule's verdict."""
    found: list[EnvBuilder] = []
    for func in ast.walk(ast.parse(source)):
        if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        nodes = list(_own_nodes(func))
        assigned: dict[str, list[ast.AST]] = {}
        builders: dict[str, int] = {}
        for node in nodes:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned.setdefault(target.id, []).append(node.value)
                        if _is_environ_copy(node.value):
                            builders[target.id] = node.lineno
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.value is not None:
                    assigned.setdefault(node.target.id, []).append(node.value)
                if _is_environ_copy(node.value):
                    builders[node.target.id] = node.lineno
        for node in nodes:
            if not isinstance(node, ast.Call) or not _is_subprocess_call(node):
                continue
            env = _env_name_of(node)
            if env is None or env not in builders:
                continue
            argv = _argv_of(node)
            runs_cli = argv is not None and _mentions_our_cli(argv, assigned)
            pops = any(line < node.lineno for line in _pop_lines(nodes, env))
            found.append(
                EnvBuilder(
                    module=module,
                    function=func.name,
                    line=builders[env],
                    runs_our_cli=runs_cli,
                    pops_window_id=pops,
                )
            )
    return found


def classify_tree(root: Path = INTEGRATION_DIR) -> list[EnvBuilder]:
    """Classify every ``*.py`` directly under ``root`` (the integration tree)."""
    found: list[EnvBuilder] = []
    for path in sorted(root.glob("*.py")):
        found.extend(classify_source(path.read_text(encoding="utf-8"), path.name))
    return found


def selected(builders: list[EnvBuilder]) -> list[EnvBuilder]:
    """The builders the rule applies to: those whose subprocess runs our own CLI."""
    return [b for b in builders if b.runs_our_cli]


def test_env_hygiene_current_tree_cli_env_builders_pop_window_id() -> None:
    """Every integration env builder that runs ``kitty_setup.cli`` pops ``KITTY_WINDOW_ID``."""
    chosen = selected(classify_tree())
    assert chosen, f"the rule selected nothing under {INTEGRATION_DIR}; it has gone vacuous"
    leaks = [f"{b.module}:{b.line} ({b.function})" for b in chosen if not b.pops_window_id]
    assert not leaks, (
        "these integration env builders run our own CLI without "
        f'env.pop("{WINDOW_ID}", None) before the subprocess call, so a run from inside a '
        f"kitty window takes the fill-current-tab branch: {leaks}"
    )


def test_guard_rule_selects_the_known_cli_env_builders() -> None:
    """The four measured CLI builders are selected; the six kitty/kitten spawners are skipped."""
    builders = classify_tree()
    chosen = {(b.module, b.function) for b in selected(builders)}
    skipped = {(b.module, b.function) for b in builders if not b.runs_our_cli}
    assert chosen >= KNOWN_CLI_BUILDERS, KNOWN_CLI_BUILDERS - chosen
    assert skipped >= KNOWN_SPAWNERS, KNOWN_SPAWNERS - skipped
    assert not KNOWN_SPAWNERS & chosen


_MISSING_POP = """
import os, subprocess, sys

def launch(socket):
    env = dict(os.environ)
    env["KITTY_LISTEN_ON"] = f"unix:{socket}"
    return subprocess.run([sys.executable, "-m", "kitty_setup.cli", "scene", "launch"], env=env)

def launch_copy(socket):
    env = os.environ.copy()
    argv = [sys.executable, "-m", "kitty_setup.cli", "scene", "launch"]
    subprocess.run(argv, env=env)
    env.pop("KITTY_WINDOW_ID", None)

def launch_ok(socket):
    env = dict(os.environ)
    env.pop("KITTY_WINDOW_ID", None)
    return subprocess.run([sys.executable, "-m", "kitty_setup.cli"], env=env)
"""


def test_guard_rule_flags_missing_pop() -> None:
    """A CLI-running builder without a pop (or popping only afterwards) is flagged."""
    builders = classify_source(_MISSING_POP, "synthetic.py")
    verdict = {b.function: (b.runs_our_cli, b.pops_window_id) for b in builders}
    assert verdict == {
        "launch": (True, False),
        "launch_copy": (True, False),
        "launch_ok": (True, True),
    }


_KITTY_SPAWNER = """
import os, subprocess

def spawn(conf, kitty, kitten, socket):
    env = dict(os.environ)
    env.pop("KITTY_LISTEN_ON", None)
    subprocess.Popen([str(kitty), f"--config={conf}", "--start-as=minimized"], env=env)
    return subprocess.run([str(kitten), "@", f"--to=unix:{socket}", "ls"], env=env)
"""


def test_guard_rule_ignores_kitty_spawner() -> None:
    """A builder that spawns ``kitty`` or ``kitten @`` directly is seen but not selected."""
    builders = classify_source(_KITTY_SPAWNER, "synthetic.py")
    assert len(builders) == 2
    assert not selected(builders)
