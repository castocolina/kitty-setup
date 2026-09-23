# Phase 6: Pane Color Cycle - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22
**Phase:** 6-Pane Color Cycle
**Areas discussed:** The `none` slot, tab accent scope, palette file format, chord invocation
**Mode:** discuss + `--analyze` overlay (trade-off table before each question; requested as `—analyze`)

**Not re-opened** (settled earlier): `ctrl+shift+alt+c` as the chord and its availability on both
OSes (Phase 4), no colour transformation (the user's PRD-round correction), scenes living at
`$XDG_CONFIG_HOME/kitty-setup/`.

---

## Findings presented before the questions

Measured on the live host, not assumed. Two expected problems evaporated and one unflagged one
appeared.

1. **Latency is a non-issue.** `kitten` is a Go binary spawning in ~10 ms and `my-kitty --help`
   runs in ~45 ms (both timed 3×). Three calls plus a CLI start sit an order of magnitude under the
   300 ms target, so no mechanism needed choosing for speed — which changed what the R4.4 question
   was actually about.
2. **All nine palette entries already resolve** through `normalize_color`
   (`blue→#0000ff` … `gray→#bebebe`, `none→NONE`). No colour-table work.
3. **`none` does not round-trip** — the unflagged problem. `normalize_color("none")` returns the
   reset sentinel `"NONE"`, and after a reset `get-colors` reports the *configured default*
   background, so a pane's cycle position is unrecoverable from its own colour.

Also confirmed: `kitten @ get-colors` accepts `--match`, so reading the focused pane is direct.

---

## The `none` slot (R4.3)

| Option | Description | Selected |
|--------|-------------|----------|
| Unknown → first, warn on collision | R4.3 as written, plus detection of a default bg equal to a palette hex | ✓ |
| Unknown → first, no collision check | R4.3 exactly, nothing added | |
| Compare against configured default | Treat "pane bg == default" as deliberately the `none` slot | |

**User's choice:** Unknown → first, warn on collision.
**Notes:** The apparent ambiguity turned out not to be a defect — a reset pane and a fresh pane are
both "off the wheel" and both should advance to `blue`. What needed handling was the narrow real
failure: a configured default background equal to a palette entry makes that entry unreachable and
the cycle silently skips it. Surfacing that rather than misbehaving quietly is the R2.8 principle
applied outside `keys`. Recorded as a prerequisite (D-03): an experiment pins `get-colors`' exact
output format for both a set and a just-reset pane before any comparison logic is written, with
matching done on `normalize_color`-normalised values so `blue` and `#0000ff` are one position.

---

## Tab accent scope (R4.1)

| Option | Description | Selected |
|--------|-------------|----------|
| Always, last-write-wins | Chord always sets pane bg + tab accent; most recently cycled pane wins the tab | ✓ |
| Solo-tab only | Recolour the tab only when `kitten @ ls` proves the tab holds one window | |
| Make it a flag | Default always, with `--no-tab` to suppress | |

**User's choice:** Always, last-write-wins.
**Notes:** R4.1 words it as an unconditional pair, and `set-tab-color` is tab-scoped in kitty — there
is no per-pane tab accent, so some pane must win. The solo-tab guard already exists at
`launcher.py:175`, but it protects a *destructive* decision (piling windows onto a populated tab,
where being wrong loses layout); recolouring is non-destructive and instantly re-triggerable, so
reusing it would buy little while making one chord behave two ways depending on pane count — the
problem rejected in Phase 4 D-04. The flag option was rejected as CLI surface for a chord-driven
feature nobody asked to split.

---

## Palette file format (R4.2)

| Option | Description | Selected |
|--------|-------------|----------|
| TOML — `palette.toml` | Ordered list beside `scenes/`, reusing the `tomllib` loader | ✓ |
| Plain lines — `palette.conf` | One name per line with `#` comments, like `intentional-overrides.conf` | |
| Inside an existing file | Fold the palette into a broader config file | |

**User's choice:** TOML.
**Notes:** Decided on Phase 7 alignment rather than on ergonomics — R5.1 already puts presets in
user TOML, so a line-based choice here would force either a second format or contorted presets
later. One format, one loader, one error path. Seeding reuses `seed_scenes()`'s copy-if-absent
contract so a user-edited palette is never overwritten. Recorded as D-06: entries validate through
`normalize_color` at load time with an error naming file/entry/line, and a missing or empty palette
falls back to the built-in default order — the chord has nowhere to display a parse error.

---

## Chord invocation (R4.4)

Reframed before asking: since latency is not a constraint, the question is whether the chord runs
the *same* code path a shell invocation does.

| Option | Description | Selected |
|--------|-------------|----------|
| `launch --type=background` | One `map` line running the real `my-kitty window cycle-color` | ✓ |
| `remote_control_script` | Python script inside kitty's own process | |
| `map … remote_control set-colors …` | Static RC command, no process | |

**User's choice:** `launch --type=background`.
**Notes:** The only option where chord and shell command are provably the same behaviour, which is
what makes success criterion 1 testable and what R4.1's "exactly the existing behaviours" demands.
`remote_control_script` was rejected as a second implementation of the cycle inside kitty's runtime,
outside the existing harness, despite being faster. The static `remote_control` map line is
impossible — choosing the next colour requires reading the current one. Open item recorded as D-08:
whether `KITTY_WINDOW_ID` and socket resolution reach a `--type=background` launch. Grounds for
expecting yes are real (`launcher._origin_window()` reads that variable, and Phase 2's R1.6 exists
because it leaks into test environments) but the `background` launch type specifically is untested,
with `--match id:@active-kitty-window-id` as the fallback the same experiment decides.

---

## Claude's Discretion

- New `scenes/cycle.py` vs extending `background.py`; the next-colour function's signature.
- `--reverse` / `--match` / `--to` plumbing; reusing `_resolve_socket` unchanged.
- How the ≤300 ms assertion is measured, given it is not a binding constraint.
- Where the D-02 collision warning surfaces (`doctor`, the cycle path, or both).
- Plan decomposition under `granularity: fine`.

## Decided without a question

- **Fail-soft on the two-call update** — the house style for multi-step remote control
  (`_apply_bg`, `_fail_soft` in `launcher.py`): print stderr, record the first non-zero exit, never
  raise mid-sequence. A failed tab accent must not leave the user unsure whether the background
  changed.
- **Payload placement** — the chord's `map` line lands under `scenes/` per Phase 5 D-01/D-02,
  because it depends on remote control, which is scenes-owned. Not the payload root.
- **Oracle cadence** — adding a chord moves `my-kitty keys` output and `doctor`'s `<N> ours` count;
  both change in the same plan as the `map` line, with the Phase 3 oracle green afterwards.

## Deferred Ideas

- **macOS verification** of the chord, the launch mechanism, and `get-colors` output — Phase 10.
- **Multiple named palettes** — TOML was chosen partly to keep this open; not in scope.
- **Palette-aware tab completion** — cheap follow-on, not required by R4.4.
- **Per-pane opacity** — already settled as impossible in kitty
  (`docs/repro/h26-perpane-opacity.md`); not revisited.
- **Presets and chord→scene** (R5.1, R5.3) — Phase 7, which reuses this phase's TOML choice.
