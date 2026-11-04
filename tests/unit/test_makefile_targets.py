"""Text-level tests for the ``Makefile``'s ``clean`` target (R1.2, D-04).

The defect is a text mismatch: the ``clean`` help line promised to keep kitty
while the recipe forwarded no ``--keep-*`` flag, so ``make clean`` removed
``kitty.app``, the symlink, the desktop entry and every backup. Executing
``make clean`` here would need a faked ``~/.local``, a faked ``PATH`` and a real
``my-kitty``, and a leak would delete real files; the behavioural half is covered
in ``test_installer_uninstall.py`` by driving ``cli_uninstall`` with the flags
parsed out of this same recipe.

Both halves are read from the file's own text: the recipe is the tab-indented
lines under ``clean:``, and the help line is the ``@echo "  clean `` line. Neither
is located by line number.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

MAKEFILE: Final[Path] = Path(__file__).resolve().parents[2] / "Makefile"
_KEEP_FLAG: Final[re.Pattern[str]] = re.compile(r"--keep-([a-z]+)")
_KEEPS_CLAUSE: Final[re.Pattern[str]] = re.compile(r"\(keeps ([^)]*)\)\"$")


def _lines() -> list[str]:
    return MAKEFILE.read_text(encoding="utf-8").splitlines()


def _clean_recipe() -> list[str]:
    """The tab-indented recipe lines directly under the one ``clean:`` target line."""
    lines = _lines()
    starts = [i for i, line in enumerate(lines) if line.startswith("clean:")]
    assert len(starts) == 1, f"expected exactly one clean: target, found {len(starts)}"
    recipe: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if not line.startswith("\t"):
            break
        recipe.append(line)
    assert recipe, "clean: target has no recipe lines"
    return recipe


def _recipe_keep_suffixes() -> set[str]:
    return {m for line in _clean_recipe() for m in _KEEP_FLAG.findall(line)}


def test_clean_recipe_passes_keep_kitty_and_keep_backups() -> None:
    recipe = _clean_recipe()
    uninstall = [line for line in recipe if "my-kitty uninstall" in line]
    assert len(uninstall) == 1, f"recipe={recipe!r}"
    flags = set(_KEEP_FLAG.findall(uninstall[0]))
    assert {"kitty", "backups"} <= flags, f"uninstall line={uninstall[0]!r}"
    assert "config" not in flags, "clean must still strip our config block"
    assert any("rm -rf tmp/" in line for line in recipe), f"recipe={recipe!r}"


def test_clean_help_keep_set_equals_recipe_flag_set() -> None:
    """The help line's ``(keeps a + b)`` set equals the recipe's ``--keep-*`` suffix set.

    Set equality in both directions and no mapping table: a promise with no flag and a
    flag the help does not mention both fail.
    """
    helps = [line for line in _lines() if line.startswith('\t@echo "  clean ')]
    assert len(helps) == 1, f"expected exactly one clean help line, found {helps!r}"
    match = _KEEPS_CLAUSE.search(helps[0])
    assert match is not None, f"help line has no trailing (keeps ...) clause: {helps[0]!r}"
    promised = {item.strip() for item in match.group(1).split("+")}
    assert promised == _recipe_keep_suffixes()
