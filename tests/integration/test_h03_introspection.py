"""Integration test for ``kitty_setup.binding_introspection``.

Drives the real ``~/.local/kitty.app/bin/kitty +runpy`` against a scratch
config dir that includes the live ``config/kitty/{windowing,bindings}.conf``.
Asserts the report shape, override classification, and the expected
``ctrl+shift+-`` regression that probe-04 surfaced.

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from kitty_setup import binding_introspection as bi

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_SOURCE = REPO_ROOT / "config" / "kitty"


@pytest.fixture()
def scratch_config(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes our payload via absolute paths.

    Returns ``(conf_path, payload_dir)``. The conf file ``include``s the
    promoted ``windowing.conf`` and ``bindings.conf`` from the repo by
    absolute path; the payload dir contains those plus
    ``intentional-overrides.conf``.
    """
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in ("windowing.conf", "bindings.conf", "intentional-overrides.conf"):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n" f"include {payload_dir / 'bindings.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_h03_introspection_reports_expected_shape(scratch_config: tuple[Path, Path]) -> None:
    conf_path, payload_dir = scratch_config
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)

    assert report.ours_count == 6
    assert (
        report.defaults_count >= 50
    )  # kitty 0.46 ships ~64; lower bound is robust to version drift.
    assert report.conflicts_count == 1, (
        f"expected exactly one conflict (ctrl+shift+- shadowing change_font_size), "
        f"got {report.conflicts_count}"
    )

    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    intentional = ["ctrl+shift+t", "ctrl+shift+n", "ctrl+shift+enter", "ctrl+shift+k"]
    for chord in intentional:
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert b.override_of is not None, f"{chord} should be marked as overriding a default"
        assert b.conflicts_with == (), f"{chord} is allow-listed; should not be flagged as conflict"

    # ctrl+shift+- is the regression probe-04 surfaced; should be flagged as a conflict.
    assert "ctrl+shift+-" in by_chord
    minus = by_chord["ctrl+shift+-"]
    assert minus.override_of is None
    assert any("change_font_size" in c for c in minus.conflicts_with)

    # vsplit binding has no kitty default collision; no annotation.
    assert "ctrl+shift+\\" in by_chord
    vsplit = by_chord["ctrl+shift+\\"]
    assert vsplit.override_of is None
    assert vsplit.conflicts_with == ()


def test_h03_render_text_includes_summary(scratch_config: tuple[Path, Path]) -> None:
    conf_path, payload_dir = scratch_config
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    text = report.render_text()
    assert "windowing (5 bindings)" in text
    assert "bindings (1 bindings)" in text
    assert "kitty defaults" in text
    assert "Summary: 6 ours" in text
    assert "1 conflict." in text


def test_h03_repeated_runs_are_byte_identical(scratch_config: tuple[Path, Path]) -> None:
    conf_path, payload_dir = scratch_config
    a = bi.enumerate_bindings(conf_path, payload_dir=payload_dir).render_text()
    b = bi.enumerate_bindings(conf_path, payload_dir=payload_dir).render_text()
    assert a == b
