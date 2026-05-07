"""Integration test for ``kitty_setup.binding_introspection``.

Drives the real ``~/.local/kitty.app/bin/kitty +runpy`` against a scratch
config dir that includes the live ``config/kitty/{windowing,clear}.conf``.
Asserts the report shape, override classification, and the post-collision-fix
attribution of ``ctrl+shift+-`` and ``ctrl+shift+/``.

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from kitty_setup import binding_introspection as bi

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_SOURCE = REPO_ROOT / "config" / "kitty"

# Conf payload files that ship `map` lines (parsed by kitty). Listed in the
# order they are `include`d from the scratch kitty.conf. To add a new category,
# append it here — the assertions below derive their expected counts from these
# files, so no number bumps are needed.
INCLUDED_PAYLOADS: tuple[str, ...] = (
    "windowing.conf",
    "clear.conf",
    "tab-nav.conf",
    "window-nav.conf",
    "font-zoom.conf",
    "detach.conf",
    "broadcast.conf",
    "url-hints.conf",
)
# Additional files copied into the payload dir but NOT included by kitty
# (metadata consumed by our introspection module).
METADATA_PAYLOADS: tuple[str, ...] = ("intentional-overrides.conf",)

_MAP_LINE = re.compile(r"^\s*map\s+")


def _count_map_lines(path: Path) -> int:
    """Count ``^\\s*map\\s+`` lines in a kitty conf file."""
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if _MAP_LINE.match(line))


@pytest.fixture()
def scratch_config(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes our payload via absolute paths.

    Returns ``(conf_path, payload_dir)``. The conf file ``include``s every
    entry of :data:`INCLUDED_PAYLOADS` by absolute path; the payload dir also
    holds :data:`METADATA_PAYLOADS` (metadata for our introspection module,
    not parsed by kitty).
    """
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (*INCLUDED_PAYLOADS, *METADATA_PAYLOADS):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        "".join(f"include {payload_dir / name}\n" for name in INCLUDED_PAYLOADS),
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_h03_introspection_reports_expected_shape(scratch_config: tuple[Path, Path]) -> None:
    conf_path, payload_dir = scratch_config
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)

    # ours_count == sum of `map` lines across every included payload conf.
    expected_ours = sum(_count_map_lines(payload_dir / name) for name in INCLUDED_PAYLOADS)
    assert report.ours_count == expected_ours, (
        f"expected {expected_ours} ours (sum of `map` lines across {INCLUDED_PAYLOADS!r}), "
        f"got {report.ours_count}"
    )
    assert (
        report.defaults_count >= 50
    )  # kitty 0.46 ships ~64; lower bound is robust to version drift.
    assert report.conflicts_count == 0, (
        f"expected zero conflicts after the ctrl+shift+- collision fix and "
        f"ctrl+shift+x clear move, got {report.conflicts_count}"
    )

    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    # All five intentional overrides (windowing creators + new hsplit chord +
    # clear chord) shadow a kitty default and are allow-listed.
    intentional = [
        "ctrl+shift+t",
        "ctrl+shift+n",
        "ctrl+shift+enter",
        "ctrl+shift+/",
        "ctrl+shift+x",
    ]
    for chord in intentional:
        assert chord in by_chord, f"missing our binding for {chord}"
        b = by_chord[chord]
        assert b.override_of is not None, f"{chord} should be marked as overriding a default"
        assert b.conflicts_with == (), f"{chord} is allow-listed; should not be flagged as conflict"

    # ctrl+shift+x is the clear binding, attributed to source "clear", and
    # overrides kitty's scroll_to_prompt 1 default.
    clear_binding = by_chord["ctrl+shift+x"]
    assert clear_binding.source == "clear"
    assert clear_binding.override_of == "scroll_to_prompt 1"

    # ctrl+shift+- moved off windowing in §2 (hsplit relocated to
    # ctrl+shift+/) and was re-bound under font-zoom.conf in §5 with the
    # kitty-default action change_font_size all -2.0 (true redundant rebind
    # for categorisation per design D5/D6). It MUST NOT be attributed to
    # windowing — that would mean the §2 hsplit relocation regressed.
    assert "ctrl+shift+-" in by_chord, (
        "ctrl+shift+- should be ours after font-zoom lands (§5)"
    )
    minus = by_chord["ctrl+shift+-"]
    assert minus.source == "font-zoom", (
        f"§2 hsplit relocation regressed: ctrl+shift+- should be attributed "
        f"to font-zoom (post-§5), got {minus.source!r}"
    )
    assert minus.action == "change_font_size all -2.0", (
        f"expected ctrl+shift+- to carry change_font_size all -2.0, got {minus.action!r}"
    )
    assert minus.override_of == "change_font_size all -2.0", (
        f"expected ctrl+shift+- to be a redundant rebind of the kitty default "
        f"change_font_size all -2.0, got override_of={minus.override_of!r}"
    )
    assert minus.conflicts_with == (), (
        f"ctrl+shift+- is allow-listed in font-zoom; should not be flagged as conflict, "
        f"got {minus.conflicts_with!r}"
    )

    # vsplit binding has no kitty default collision; no annotation.
    assert "ctrl+shift+\\" in by_chord
    vsplit = by_chord["ctrl+shift+\\"]
    assert vsplit.source == "windowing"
    assert vsplit.override_of is None
    assert vsplit.conflicts_with == ()

    # New hsplit chord ctrl+shift+/ is ours, attributed to windowing, and
    # shadows kitty's search_scrollback (allow-listed).
    hsplit = by_chord["ctrl+shift+/"]
    assert hsplit.source == "windowing"
    assert hsplit.override_of == "search_scrollback"
    assert hsplit.conflicts_with == ()


def test_h03_render_text_includes_summary(scratch_config: tuple[Path, Path]) -> None:
    conf_path, payload_dir = scratch_config
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    text = report.render_text()

    # Per-section header counts derive from each payload's `map` line count.
    # The section name is the conf basename (sans `.conf`).
    expected_total = 0
    for name in INCLUDED_PAYLOADS:
        section = name.removesuffix(".conf")
        count = _count_map_lines(payload_dir / name)
        expected_total += count
        assert f"{section} ({count} bindings)" in text, (
            f"expected '{section} ({count} bindings)' header in render_text() output"
        )
    assert "kitty defaults" in text
    assert f"Summary: {expected_total} ours" in text
    assert "0 conflicts." in text


def test_h03_repeated_runs_are_byte_identical(scratch_config: tuple[Path, Path]) -> None:
    conf_path, payload_dir = scratch_config
    a = bi.enumerate_bindings(conf_path, payload_dir=payload_dir).render_text()
    b = bi.enumerate_bindings(conf_path, payload_dir=payload_dir).render_text()
    assert a == b
