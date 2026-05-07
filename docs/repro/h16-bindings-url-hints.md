# H16 — url-hints category (renumbered from h08)

**Capability:** kitty-curated-bindings (Phase 1 §5, url-hints chord).

**Status:** Promoted. Configuration in
[`config/kitty/url-hints.conf`](../../config/kitty/url-hints.conf).
Autonomous test in
[`tests/integration/test_h16_bindings_url_hints.py`](../../tests/integration/test_h16_bindings_url_hints.py).

## Renumbered from h08

Tasks.md originally numbered this hypothesis h08. Following the
h11/h12/h13/h14/h15 precedent (h03 was already taken by
`test_h03_introspection.py`, and we keep `h<NN>` integers contiguous
after the late-arriving h09/h10 work), we shifted this hypothesis to
h16. design.md D7 + tasks.md §8 now say h16.

## Why this category exists

Phase 1 §5 (`design.md` D6) puts one chord into a url-hints group:

| Chord          | Our action            | Kitty default action  |
| -------------- | --------------------- | --------------------- |
| `ctrl+shift+e` | `open_url_with_hints` | `open_url_with_hints` |

The chord is a redundant rebind of a kitty default (h16 probe
finding, 2026-05-06: kitty 0.46.x already binds `ctrl+shift+e` →
`open_url_with_hints`). The map line lives in `url-hints.conf` purely
so the chord surfaces under the `url-hints` section in `my-kitty
keys` — D5 "redundant binding for `<category>.conf` categorisation"
pattern. The chord IS allow-listed in `intentional-overrides.conf`
with the standard "redundant binding for url-hints.conf
categorisation; same action as kitty default" comment.

## Manual repro

1. `make install`.
2. Open kitty. In the active window, run any command whose output
   contains a URL (e.g. `git log --oneline -1` followed by a paste of
   `https://example.com/`, or `echo https://kitty.org/`).
3. Press `ctrl+shift+e` → kitty overlays one-or-two-letter hint
   labels on every URL visible in the active window's scrollback.
4. Press the label corresponding to a URL → kitty hands the URL to
   `open_url_with` (the user's default browser unless overridden in
   `kitty.conf`). The hint overlay dismisses.
5. Press `escape` while the overlay is up → the overlay dismisses
   without opening any URL.
6. `my-kitty keys` → confirm a `url-hints (1 binding)` section listing
   `ctrl+shift+e` with action `open_url_with_hints` and the
   annotation `[overrides default open_url_with_hints]`. The summary
   line reports `0 conflicts.`

## Verifying autonomously

```
KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h16_bindings_url_hints.py -v
```

The probe builds a scratch kitty config that includes
`url-hints.conf`, runs `binding_introspection.enumerate_bindings`,
and asserts:

* The chord is attributed to `url-hints` with the expected action and
  `override_of == 'open_url_with_hints'` (redundant rebind of the
  kitty default).
* It carries no `conflicts_with` entry.
* The full report has zero conflicts.
* `my-kitty keys --json` exposes a one-entry `url-hints` section.

## Linux Status

Verified on Pop!_OS 24.04 with Kitty 0.46.2 on 2026-05-06 by the
autonomous probe (`tests/integration/test_h16_bindings_url_hints.py`).
Manual confirmation that pressing `ctrl+shift+e` opens the URL-hint
overlay and that selecting a hint opens the URL in the user's
default browser is required when running locally — the autonomous
probe asserts only chord-to-action wiring, not the hint-overlay
behaviour or the browser-launch side effect.

## macOS Status

Deferred — the agent does not have access to a macOS host. The chord
is in pure-explicit-modifier form (`ctrl+shift+e`) and the managed
entry pins `kitty_mod ctrl+shift`, so it SHOULD resolve to the same
physical chord on macOS. Manual confirmation that the chord opens
the URL-hint overlay and hands the selected URL to `open_url_with`
(the macOS default browser unless overridden) is required before
declaring §5 complete on macOS. Tracked under the umbrella
phase1-curated-bindings macOS verification follow-up.

## Known limitations

* The autonomous probe asserts chord-to-action wiring through
  `binding_introspection`. Behavioural confirmation that the chord
  opens the hint overlay and that selecting a hint launches the
  user's browser is left to the manual repro. Kitty's remote-control
  `send-key` injects raw key events without traversing the keymap,
  so the harness cannot simulate the chord press; and the hint
  overlay is itself an interactive surface, so even if the chord
  could be driven, selecting a hint would block on user input in any
  non-interactive TTY.
* The action `open_url_with_hints` honours kitty's `url_prefixes`
  and `detect_urls` settings — URLs that don't match the configured
  prefixes won't get a hint label. Tracked as a possible follow-up
  if the default prefix list ends up missing a common URL shape in
  practice.
