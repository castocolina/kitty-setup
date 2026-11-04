"""``make clean`` run from a copied Makefile, in a sandbox whose PATH holds only ``rm`` and a fake
``my-kitty`` (02-12 IN-07, WR-04, T-2-53).

The Makefile is read from the tree this test belongs to, so a materialised RED or GREEN tree tests
its own recipe. ``make`` is run by the absolute path ``shutil.which`` resolved, with ``shell=False``
and a complete env built from literals and ``tmp_path``. This module never reads ``os.environ``
and never runs the repo's own ``make``.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_MAKEFILE = Path(__file__).resolve().parents[2] / "Makefile"
_MAKE = shutil.which("make")
_RM = shutil.which("rm")


def _sandbox(tmp_path: Path, *, fake_exit: int | None) -> tuple[Path, Path, Path]:
    """Return (sandbox, bin dir, argv log). ``fake_exit`` None means no ``my-kitty`` on PATH."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    shutil.copyfile(_MAKEFILE, sandbox / "Makefile")
    (sandbox / "tmp").mkdir()
    (sandbox / "tmp" / "scratch.txt").write_text("scratch\n", encoding="utf-8")
    bin_dir = sandbox / "bin"
    bin_dir.mkdir()
    assert _RM is not None, "rm must be on PATH for the test process"
    (bin_dir / "rm").symlink_to(_RM)
    log = sandbox / "argv.log"
    if fake_exit is not None:
        fake = bin_dir / "my-kitty"
        fake.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            f"open({str(log)!r}, 'a', encoding='utf-8').write(' '.join(sys.argv[1:]) + '\\n')\n"
            f"sys.exit({fake_exit})\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
    return sandbox, bin_dir, log


def _make_clean(sandbox: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    assert _MAKE is not None, "make must be on PATH for the test process"
    return subprocess.run(
        [_MAKE, "clean"],
        cwd=sandbox,
        env={"PATH": str(bin_dir)},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_clean_failure_propagates(tmp_path: Path) -> None:
    """A failing ``my-kitty uninstall`` makes ``make clean`` exit non-zero (IN-07)."""
    sandbox, bin_dir, log = _sandbox(tmp_path, fake_exit=3)
    result = _make_clean(sandbox, bin_dir)
    assert result.returncode != 0, result.stdout + result.stderr
    assert log.read_text(encoding="utf-8").strip() == "uninstall --keep-kitty --keep-backups"


def test_guard_clean_without_my_kitty_succeeds(tmp_path: Path) -> None:
    """With no ``my-kitty`` on PATH the recipe skips uninstall and still removes ``tmp/``."""
    sandbox, bin_dir, _ = _sandbox(tmp_path, fake_exit=None)
    result = _make_clean(sandbox, bin_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (sandbox / "tmp").exists()


def test_guard_clean_passes_keep_flags(tmp_path: Path) -> None:
    """A present ``my-kitty`` is called with exactly the two keep flags, and ``make`` succeeds."""
    sandbox, bin_dir, log = _sandbox(tmp_path, fake_exit=0)
    result = _make_clean(sandbox, bin_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    assert log.read_text(encoding="utf-8").strip() == "uninstall --keep-kitty --keep-backups"
    assert not (sandbox / "tmp").exists()
