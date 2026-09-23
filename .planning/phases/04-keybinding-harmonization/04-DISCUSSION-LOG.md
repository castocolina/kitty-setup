# Phase 4: Keybinding Harmonization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22
**Phase:** 4-Keybinding Harmonization
**Areas discussed:** Per-OS mechanism, macOS cwd chord coverage, the `kitty_mod` pin, allow-list shape
**Mode:** discuss + `--analyze` overlay (trade-off table before each question; requested as `—analyze`)

**Not re-opened** (settled in earlier phases): the native-per-OS model, instant-clear chords and
semantics, the declared `cmd+k` override, and the oracle as acceptance gate.

---

## Per-OS mechanism

Constraint presented first: kitty parses `cmd+k` and `super+k` to the same chord (`mods=8`,
verified during the Phase 3 discussion), so one shared file binding both OSes' chords would
self-collide on Linux. The per-OS split is therefore a correctness requirement.

| Option | Description | Selected |
|--------|-------------|----------|
| Extend installer-side variants | Generalise `_select_clear_variant` to `<category>-linux.conf` / `<category>-mac.conf`, renamed at install | ✓ |
| kitty-side conditional include | Research whether kitty supports an OS conditional in `include` | |
| Single file, avoid colliding chords | One file per category, chords chosen to be safe on both | |

**User's choice:** Extend installer-side variants.
**Notes:** Proven pattern in this codebase (`config_updater.py:21-49`, called at `:240`), and it keeps `my-kitty keys` seeing only the host's lines — which R2.8(c) requires. The third option was rejected on substance: avoiding cross-OS collisions means giving up `cmd+t`/`cmd+n`/`cmd+enter` on macOS, which is exactly what R2.3 asks for. Scope guard recorded as D-03: only categories that actually differ get variants, and the matrix names them — no pre-emptive splitting.

---

## macOS cwd chord coverage (R2.3)

| Option | Description | Selected |
|--------|-------------|----------|
| Both `cmd+` and `ctrl+shift+` | Override whichever of the two sets kitty actually binds on macOS | ✓ |
| `cmd+` only | Leave kitty's ctrl+shift variants at their non-inheriting defaults | |

**User's choice:** Both.
**Notes:** The rejected option would make one action behave two ways depending on which chord the user pressed. Guard recorded: only chords kitty really binds get a line — the Phase 3 matrix decides which exist, so nothing is bound speculatively.

---

## The `kitty_mod` pin

| Option | Description | Selected |
|--------|-------------|----------|
| Decide from the Phase 3 matrix | Treat as an open item; drop the pin if the matrix confirms it is a no-op | ✓ |
| Drop it now | Remove on the strength of the reading so far | |
| Keep regardless | Insurance against a future kitty default change | |

**User's choice:** Decide from the matrix.
**Notes:** Current reading is that kitty 0.49 defaults `kitty_mod` to `ctrl+shift` on both OSes, which would make the pin a no-op and its neighbouring comment ("macOS defaults to cmd") false. Deferring the verdict to the matrix is consistent with the mantra — evidence before removal. Recorded either way: the comment cannot survive unchanged.

---

## Allow-list shape

| Option | Description | Selected |
|--------|-------------|----------|
| One file, OS-tagged entries | `cmd+k  # macOS: overrides clear_terminal to_cursor` | ✓ |
| Per-OS allow-lists | Variants selected at install like the payload files | |

**User's choice:** One file, OS-tagged entries.
**Notes:** No parser change needed — the introspection module already strips inline comments (`binding_introspection.py:196-209`). Per-OS files were rejected because they would hide half the justifications from any given host, defeating the file's purpose. Follow-on recorded as D-07: the existing `cmd+k` entry claims "new chord; no kitty default", which the research contradicts, so its text must change to a declared override naming `clear_terminal to_cursor`.

---

## Claude's Discretion

- Naming of the generalised selector; table-driven vs per-category selection.
- Where the per-OS chord set documentation (R2.6) lives, as long as one source is authoritative.
- How the ≤200 ms instant-clear budget is measured, provided the method is recorded.
- Plan decomposition under `granularity: fine`, subject to the oracle rule below.

## Decided without a question

- **Oracle cadence (D-09):** the Phase 3 oracle runs after every binding change in this phase, not
  once at the end, so a regression is attributable to the change that caused it. Follows from the
  oracle being the acceptance gate; a plan that leaves it red does not seal.
- **Instant clear (D-08):** chords and semantics were already locked; what this phase adds is that
  the ≤200 ms budget is asserted by a test against a real kitty session, and the
  `ctrl+shift+alt+k` fallback is tested as a first-class path rather than merely documented —
  it exists for the compositor-grab case.
- **Stale header paths:** payload file headers cite `openspec/changes/...` paths that Phase 1 moved.
  When this phase edits a header, it repoints it at `.planning/` rather than leaving a dead path.

## Deferred Ideas

- **macOS verification** of every criterion here — Phase 10 (which may also fix what it finds).
- **Binding scene chords** — Phase 7; R2.7 only verifies the chords are free.
- **`ctrl+shift+alt+c`** — bound in Phase 6; confirmed unclaimed here.
- **Repro-doc rewrites** for chords that move — Phase 8 owns doc accuracy, but a chord changed here
  must not leave a repro doc asserting the old behaviour.
