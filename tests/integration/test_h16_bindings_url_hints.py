"""H16 — url-hints category (renumbered from h08 per the h11/h12/h13/h14/h15 precedent).

Asserts:

* The promoted ``url-hints.conf`` carries one ``map`` line. The chord
  is a redundant rebind of a kitty default (probe finding h16,
  2026-05-06: kitty 0.46.x defaults ``ctrl+shift+e`` to
  ``open_url_with_hints`` — same action). The chord is allow-listed in
  ``intentional-overrides.conf`` per D5.
* ``binding_introspection.enumerate_bindings`` reports the chord under
  source ``url-hints`` with the expected action and ``override_of ==
  'open_url_with_hints'`` (redundant-rebind annotation). It carries no
  ``conflicts_with``.
* ``my-kitty keys --json`` (via ``Report.to_json``) exposes a
  ``url-hints`` section with one entry and ``summary.conflicts == 0``.

Note: chord-driven keystrokes via ``send-key`` cannot exercise our key
bindings (kitty remote control injects key events without running them
through the keymap). The chord-to-action wiring is validated through the
binding-introspection module instead, which is the same mechanism backing
``my-kitty keys`` / the doctor's ``bindings`` check. Behavioural
confirmation that pressing the chord opens the URL-hint overlay (and that
selecting a hint opens the URL in the user's browser) lives in the manual
repro doc — kitty remote control's ``send-key`` cannot drive interactive
overlays.

Gated by ``KITTI_INTEGRATION=1`` per ``tests/conftest.py``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from kitty_setup import binding_introspection as bi

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_SOURCE = REPO_ROOT / "config" / "kitty"

EXPECTED_ACTIONS: dict[str, str] = {
    "ctrl+shift+e": "open_url_with_hints",
}


@pytest.fixture()
def url_hints_conf() -> str:
    """Return the promoted ``config/kitty/url-hints.conf`` text."""
    return (PAYLOAD_SOURCE / "url-hints.conf").read_text()


@pytest.fixture()
def url_hints_scratch(tmp_path: Path) -> tuple[Path, Path]:
    """Build a scratch ``kitty.conf`` that includes our payload (with url-hints).

    Returns ``(conf_path, payload_dir)``. The conf file ``include``s the
    promoted ``windowing.conf``, ``clear.conf``, ``tab-nav.conf``,
    ``window-nav.conf``, ``font-zoom.conf``, ``detach.conf``,
    ``broadcast.conf`` and ``url-hints.conf`` from the repo by absolute
    path; the payload dir contains those plus
    ``intentional-overrides.conf``.
    """
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    for name in (
        "windowing.conf",
        "clear.conf",
        "tab-nav.conf",
        "window-nav.conf",
        "font-zoom.conf",
        "detach.conf",
        "broadcast.conf",
        "url-hints.conf",
        "intentional-overrides.conf",
    ):
        shutil.copy(PAYLOAD_SOURCE / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n"
        f"include {payload_dir / 'tab-nav.conf'}\n"
        f"include {payload_dir / 'window-nav.conf'}\n"
        f"include {payload_dir / 'font-zoom.conf'}\n"
        f"include {payload_dir / 'detach.conf'}\n"
        f"include {payload_dir / 'broadcast.conf'}\n"
        f"include {payload_dir / 'url-hints.conf'}\n",
        encoding="utf-8",
    )
    return conf_path, payload_dir


def test_url_hints_conf_carries_one_map_line(url_hints_conf: str) -> None:
    """``url-hints.conf`` carries the one expected ``map`` line verbatim."""
    map_lines = [
        line.strip()
        for line in url_hints_conf.splitlines()
        if line.lstrip().startswith("map ")
    ]
    assert len(map_lines) == 1, (
        f"expected exactly 1 map line in url-hints.conf, got {len(map_lines)}: {map_lines!r}"
    )
    for chord, action in EXPECTED_ACTIONS.items():
        assert any(
            line.startswith(f"map {chord} ") and line.endswith(action)
            for line in map_lines
        ), f"missing or wrong map line for {chord} -> {action} in {map_lines!r}"


def test_introspection_reports_url_hints_section(
    url_hints_scratch: tuple[Path, Path],
) -> None:
    """The chord registers under ``url-hints`` with the expected action.

    The chord is a redundant rebind of a kitty default (probe finding
    h16: kitty 0.46.x defaults ``ctrl+shift+e`` to
    ``open_url_with_hints``), so ``override_of`` carries the default
    action string and the chord is allow-listed — no
    ``conflicts_with`` entry, zero report-level conflicts.
    """
    conf_path, payload_dir = url_hints_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord_ours = {
        b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE
    }

    for chord, expected_action in EXPECTED_ACTIONS.items():
        assert chord in by_chord_ours, f"missing our binding for {chord}"
        b = by_chord_ours[chord]
        assert b.source == "url-hints", (
            f"{chord} should be attributed to url-hints, got {b.source!r}"
        )
        assert b.action == expected_action, (
            f"{chord} should be bound to {expected_action!r}, got {b.action!r}"
        )
        assert b.override_of == expected_action, (
            f"{chord} is a redundant rebind of the kitty default "
            f"{expected_action!r}; expected override_of=={expected_action!r}, "
            f"got {b.override_of!r}. If this fires, kitty's default for the "
            f"chord changed (or our action string drifted) — re-probe."
        )
        assert b.conflicts_with == (), (
            f"{chord} is allow-listed; should not be flagged as a conflict, "
            f"got {b.conflicts_with!r}"
        )

    url_hints_entries = [b for b in report.bindings if b.source == "url-hints"]
    assert len(url_hints_entries) == 1, (
        f"expected exactly 1 entry under source 'url-hints', got "
        f"{len(url_hints_entries)}"
    )
    assert report.conflicts_count == 0, (
        f"expected 0 conflicts after url-hints category lands, got "
        f"{report.conflicts_count}"
    )


def test_keys_json_exposes_url_hints_section(
    url_hints_scratch: tuple[Path, Path],
) -> None:
    """``my-kitty keys --json`` payload carries one ``url-hints`` entry."""
    conf_path, payload_dir = url_hints_scratch
    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    payload = json.loads(report.to_json())

    url_hints_entries = [
        b for b in payload["bindings"] if b["source"] == "url-hints"
    ]
    assert len(url_hints_entries) == 1, (
        f"expected 1 url-hints entry in JSON output, got "
        f"{len(url_hints_entries)}: {url_hints_entries!r}"
    )
    chords_to_actions = {b["chord"]: b["action"] for b in url_hints_entries}
    assert chords_to_actions == EXPECTED_ACTIONS, (
        f"url-hints JSON entries do not match expected mapping; got "
        f"{chords_to_actions!r}"
    )
    assert payload["summary"]["conflicts"] == 0
