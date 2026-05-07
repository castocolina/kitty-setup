"""H02/H09 — one keystroke clears screen + scrollback instantly.

Promoted from ``tmp/h02-instant-clear/run.py``. See
``docs/repro/h09-bindings-clear-relocation.md`` for the manual repro and the
explanation of the binding's two-stage combine. The chord moved from
``ctrl+shift+k`` to ``ctrl+shift+x`` as part of phase1-curated-bindings
(`ctrl+shift+k` is now reserved for vim-style window-nav-up).

The behavioural half (`clear_terminal scrollback active` + `send_text \x0c`
clears the screen and scrollback) is exercised via ``session.action`` /
``session.send_text`` rather than ``session.send_key`` — kitty's remote
control ``send-key`` injects raw key events that do NOT traverse the keymap,
so chord-triggered behaviour cannot be exercised through the harness. The
chord registration itself is validated through the introspection module:
``my-kitty keys`` confirms the chord lives on ``ctrl+shift+x`` under source
``clear`` and that the old chord ``ctrl+shift+k`` is no longer one of ours.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from kitty_setup import binding_introspection as bi
from kitty_setup.harness.kitty_session import KittySession

NUM_MARKERS = 50
RENDER_DELAY_S = 0.4
RPC_BUDGET_MS = 200.0

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_clear_conf_binds_new_chord_and_drops_old(clear_conf: str) -> None:
    """The promoted clear.conf binds ctrl+shift+x; ctrl+shift+k is no longer a `map`."""
    assert "ctrl+shift+x combine" in clear_conf, (
        f"expected ctrl+shift+x combine map line in clear.conf; got:\n{clear_conf}"
    )
    map_lines = [
        line
        for line in clear_conf.splitlines()
        if line.lstrip().startswith("map ") and "ctrl+shift+k" in line
    ]
    assert map_lines == [], f"ctrl+shift+k must not be a map line in clear.conf; got {map_lines}"


def test_clear_wipes_screen_and_scrollback(clear_conf: str) -> None:
    """The combine action (clear_terminal scrollback + form-feed) wipes both buffers.

    Exercised via the action API (the chord behaviour is identical, but
    ``send-key`` over remote control bypasses keymaps).
    """
    with KittySession(config_snippets=[clear_conf]) as session:
        cmd = f'for i in $(seq 1 {NUM_MARKERS}); do echo "marker-$i"; done\r'
        session.send_text(cmd)
        time.sleep(RENDER_DELAY_S)

        before = session.get_text(extent="all")
        markers_before = sum(1 for i in range(1, NUM_MARKERS + 1) if f"marker-{i}" in before)
        assert markers_before > 0, "expected markers to render before the clear"

        t0 = time.monotonic()
        session.action("clear_terminal", "scrollback", "active")
        session.send_text("\x0c")
        elapsed_ms = (time.monotonic() - t0) * 1000.0

        time.sleep(RENDER_DELAY_S)
        after = session.get_text(extent="all")
        markers_after = sum(1 for i in range(1, NUM_MARKERS + 1) if f"marker-{i}" in after)
        assert (
            markers_after == 0
        ), f"expected 0 markers after clear, got {markers_after}; text={after!r}"

        session.send_text("echo post-clear\r")
        time.sleep(RENDER_DELAY_S)
        post = session.get_text(extent="all")
        assert "post-clear" in post, f"expected post-clear in {post!r}"

        assert (
            elapsed_ms < RPC_BUDGET_MS
        ), f"clear RPC took {elapsed_ms:.1f}ms; budget {RPC_BUDGET_MS}ms"


def test_clear_chord_is_registered_under_clear_source(tmp_path: Path) -> None:
    """``my-kitty keys`` reports the new chord under ``clear`` and drops the old chord."""
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    payload_source = REPO_ROOT / "config" / "kitty"
    for name in ("windowing.conf", "clear.conf", "intentional-overrides.conf"):
        shutil.copy(payload_source / name, payload_dir / name)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n"
        f"include {payload_dir / 'clear.conf'}\n",
        encoding="utf-8",
    )

    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord = {b.chord: b for b in report.bindings if b.source != bi.DEFAULT_SOURCE}

    assert "ctrl+shift+x" in by_chord, "ctrl+shift+x missing from our bindings"
    clear_binding = by_chord["ctrl+shift+x"]
    assert clear_binding.source == "clear", (
        f"clear binding should be attributed to source 'clear', got {clear_binding.source!r}"
    )
    assert "combine" in clear_binding.action, (
        f"clear binding action should be the combine: clear_terminal + send_text form, "
        f"got {clear_binding.action!r}"
    )

    if "ctrl+shift+k" in by_chord:
        pytest.fail(
            f"ctrl+shift+k should not be one of our bindings any more; "
            f"got {by_chord['ctrl+shift+k']}"
        )
