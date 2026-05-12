"""H02/H09 — one keystroke clears screen + scrollback instantly.

After phase1-curated-bindings-revert-defaults the chord under test is the
host-OS-native instant-clear:

* Linux: ``super+k`` (plus ``ctrl+shift+alt+k`` cross-OS fallback).
* macOS: ``cmd+k`` (plus ``ctrl+shift+alt+k`` cross-OS fallback).

``ctrl+shift+x`` was the previous chord; that chord now returns to kitty's
default ``scroll_to_prompt 1``. See
``docs/repro/h20-bindings-clear-relocation-superK.md`` and design D5.

The behavioural half (`clear_terminal scrollback active` + `send_text \\x0c`
clears the screen and scrollback) is exercised via ``session.action`` /
``session.send_text`` rather than ``session.send_key`` — kitty's remote
control ``send-key`` injects raw key events that do NOT traverse the keymap,
so chord-triggered behaviour cannot be exercised through the harness. The
chord registration itself is validated through the introspection module:
``my-kitty keys`` confirms each chord lives under source ``clear``.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

from kitty_setup import binding_introspection as bi
from kitty_setup.harness.kitty_session import KittySession
from tests.integration._helpers import copy_clear_payload

NUM_MARKERS = 50
RENDER_DELAY_S = 0.4
RPC_BUDGET_MS = 200.0

REPO_ROOT = Path(__file__).resolve().parents[2]
PAYLOAD_SOURCE = REPO_ROOT / "config" / "kitty"

# Per-OS native instant-clear chord (D5). The cross-OS fallback chord is
# tested as a second case below.
NATIVE_CHORD: str = "cmd+k" if sys.platform == "darwin" else "super+k"
FALLBACK_CHORD: str = "ctrl+shift+alt+k"


def test_clear_conf_binds_new_chords_and_drops_old(clear_conf: str) -> None:
    """The deployed clear payload binds the OS-native chord + the fallback, and
    no longer carries ``ctrl+shift+x`` or ``ctrl+shift+k``."""
    assert f"map {NATIVE_CHORD}" in clear_conf, (
        f"expected host-OS-native chord {NATIVE_CHORD!r} map line in "
        f"clear-*.conf; got:\n{clear_conf}"
    )
    assert f"map {FALLBACK_CHORD}" in clear_conf, (
        f"expected fallback chord {FALLBACK_CHORD!r} map line in "
        f"clear-*.conf; got:\n{clear_conf}"
    )
    forbidden_chords = ("ctrl+shift+x", "ctrl+shift+k")
    map_lines = [line for line in clear_conf.splitlines() if line.lstrip().startswith("map ")]
    for forbidden in forbidden_chords:
        leakage = [line for line in map_lines if forbidden in line]
        assert (
            leakage == []
        ), f"{forbidden} must not be a map line in clear-*.conf any more; got {leakage}"


def test_clear_wipes_screen_and_scrollback(clear_conf: str) -> None:
    """The combine action (clear_terminal scrollback + form-feed) wipes both buffers.

    Exercised via the action API (the chord behaviour is identical, but
    ``send-key`` over remote control bypasses keymaps). This covers the
    behavioural half for both the native chord and the fallback chord —
    they bind the same action.
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


def test_clear_chord_registered_under_clear_source(tmp_path: Path) -> None:
    """Both clear chords surface under source ``clear`` and ``ctrl+shift+x`` is released."""
    payload_dir = tmp_path / "kitty-setup"
    payload_dir.mkdir()
    shutil.copy(PAYLOAD_SOURCE / "windowing.conf", payload_dir / "windowing.conf")
    shutil.copy(
        PAYLOAD_SOURCE / "intentional-overrides.conf",
        payload_dir / "intentional-overrides.conf",
    )
    copy_clear_payload(payload_dir)
    conf_path = tmp_path / "kitty.conf"
    conf_path.write_text(
        f"include {payload_dir / 'windowing.conf'}\n" f"include {payload_dir / 'clear.conf'}\n",
        encoding="utf-8",
    )

    report = bi.enumerate_bindings(conf_path, payload_dir=payload_dir)
    by_chord_ours: dict[str, bi.Binding] = {}
    for b in report.bindings:
        if b.source != bi.DEFAULT_SOURCE:
            by_chord_ours[b.chord] = b

    # Both clear chords are registered as ours under source `clear`.
    for chord in (NATIVE_CHORD, FALLBACK_CHORD):
        assert chord in by_chord_ours, f"{chord} missing from our bindings"
        b = by_chord_ours[chord]
        assert (
            b.source == "clear"
        ), f"clear binding {chord} should be attributed to source 'clear', got {b.source!r}"
        assert "combine" in b.action, (
            f"clear binding {chord} action should be the combine: clear_terminal + send_text form, "
            f"got {b.action!r}"
        )

    # The legacy ctrl+shift+x is no longer ours.
    assert "ctrl+shift+x" not in by_chord_ours, (
        f"ctrl+shift+x must not be one of our bindings any more; "
        f"got {by_chord_ours.get('ctrl+shift+x')}"
    )

    # And kitty's default ctrl+shift+x = scroll_to_prompt 1 is back.
    by_chord_default = {b.chord: b for b in report.bindings if b.source == bi.DEFAULT_SOURCE}
    assert "ctrl+shift+x" in by_chord_default, "ctrl+shift+x expected back under kitty defaults"
    assert (
        "scroll_to_prompt" in by_chord_default["ctrl+shift+x"].action
    ), f"expected scroll_to_prompt on ctrl+shift+x, got {by_chord_default['ctrl+shift+x'].action!r}"
