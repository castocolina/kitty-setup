"""H02 — one keystroke clears screen + scrollback instantly.

Promoted from ``tmp/h02-instant-clear/run.py``. See ``docs/repro/h02-clear.md``
for the manual repro and the explanation of the binding's two-stage combine.
"""

from __future__ import annotations

import time

from kitty_setup.harness.kitty_session import KittySession

NUM_MARKERS = 50
RENDER_DELAY_S = 0.4
RPC_BUDGET_MS = 200.0


def test_clear_wipes_screen_and_scrollback(bindings_conf: str) -> None:
    with KittySession(config_snippets=[bindings_conf]) as session:
        cmd = f'for i in $(seq 1 {NUM_MARKERS}); do echo "marker-$i"; done\r'
        session.send_text(cmd)
        time.sleep(RENDER_DELAY_S)

        before = session.get_text(extent="all")
        markers_before = sum(1 for i in range(1, NUM_MARKERS + 1) if f"marker-{i}" in before)
        assert markers_before > 0, "expected markers to render before the clear"

        # Mirror the combine: clear scrollback + Ctrl-L (the bash readline
        # clear-screen binding). The keybinding does the same two ops with
        # `combine : clear_terminal scrollback active : send_text ... \x0c`.
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
