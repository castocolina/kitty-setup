# Phase 3: Keybinding Research & Oracle - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-22
**Phase:** 3-Keybinding Research & Oracle
**Areas discussed:** Oracle source, sequence rendering, source-assertion scope, chord normalisation
**Mode:** discuss + `--analyze` overlay (trade-off table before each question; requested as `—analyze`)

---

## Findings presented before the questions

Both came from scouting kitty 0.49 directly, and both changed what the phase must do.

1. **`my-kitty keys` misrepresents sequence bindings.** `opts.keyboard_modes[""].keymap` keys on the
   *prefix* chord; each `KeyDefinition` carries the remainder in `.rest`, which
   `_RUNPY_SNIPPET` drops. Result: `ctrl+shift+p` printed 10 times with 10 actions,
   `ctrl+shift+a` 4 times. Pre-existing, and exactly the phantom/duplicate class R2.8(d) forbids.
   Affects 2 chords in kitty 0.49's defaults; 101 definitions total, matching today's 22 ours +
   79 defaults.
2. **kitty cannot report a binding's origin.** `definition_location.filename` is empty for all 101
   definitions, confirming the original probe — so `_walk_payload` stays necessary and the oracle
   cannot verify `source` against kitty.

Also established: `kitty --debug-config` is not a CLI flag (it is a mappable action), so the
doctor label Phase 2 fixes was wrong twice over.

---

## Oracle source (R2.8)

| Option | Description | Selected |
|--------|-------------|----------|
| kitty's own `debug_config`/`ShortcutMap` renderer | Parse what kitty formats; independent of our modifier arithmetic and `.rest` handling | ✓ |
| Second independent runpy snippet | Deliberately different keymap walk | |
| Live session over remote control | kitty exposes no keymap verb | |
| Committed golden file | Freeze expected output for a pinned kitty version | |

**User's choice:** kitty's own renderer.
**Notes:** Selected because it is the only candidate that would have caught both findings above — the chord strings come from kitty rather than from us. Confirmed present in kitty 0.49: `kitty.debug_config` exports `debug_config`, `print_mapping_changes`, `compare_maps`, `mod_to_names`, `ShortcutMap`. Recorded as `costly` reversibility: the oracle gates Phases 4, 7 and 10, so changing its source later means re-proving every binding change judged against it.

---

## Sequence rendering

| Option | Description | Selected |
|--------|-------------|----------|
| Full sequence chord | `ctrl+shift+p > f`, built from `.rest` | ✓ |
| Prefix with a count | `ctrl+shift+p — 10 sequence bindings` | |
| Omit sequences | Show single-chord bindings only | |

**User's choice:** Full sequence chord.
**Notes:** The only option where every printed line is a real binding. Rejected alternatives either hide what the sequences do or hide bindings that could collide with ours. Consequence noted for planning: doctor's counts shift, so expected values and any asserting test must change in the same plan.

---

## Source-assertion scope

| Option | Description | Selected |
|--------|-------------|----------|
| Split the assertion | Oracle compares chord+action 1:1; attribution proven by targeted fixture tests | ✓ |
| Keep source in the oracle | Oracle reconstructs expected source from the payload files | |

**User's choice:** Split the assertion.
**Notes:** Forced by finding 2 — kitty has no origin data to compare against. The rejected option would have re-implemented the code under test inside the test, so a shared misunderstanding would pass both. ROADMAP criterion 1 was reworded from "chord, action, and source" to match, with the fixture cases named: a chord only our payload defines, a pure kitty default, a redundant rebind, and a user `kitty.conf` line outside our block.

---

## Chord normalisation (R1.8)

| Option | Description | Selected |
|--------|-------------|----------|
| kitty's `parse_shortcut` | Normalise payload chords through kitty in the same runpy call | ✓ |
| Python alias table | Maintain our own cmd→super / opt→alt mapping | |

**User's choice:** kitty's parser.
**Notes:** Exact by construction — `parse_shortcut('cmd+k')` and `parse_shortcut('super+k')` both return `mods=8, key_name='k'`, verified during the discussion. Covers every alias kitty accepts without us tracking them. The payload walk already depends on kitty for the keymap, so this adds a round trip rather than a new dependency. R1.8's text was updated with the mechanism and its Phase 3 ownership.

---

## Claude's Discretion

- Whether `keys --json` gains explicit sequence/shadowed fields or encodes them in the chord string.
- How `debug_config` output is parsed, and whether the oracle keeps a reusable helper.
- Hypothesis directory numbering and internal layout for the R2.5 experiment.
- Plan decomposition under `granularity: fine`, provided the oracle lands before anything it judges.

## Decided without a question

- **Oracle strictness (D-04):** exact equality, no tolerance list; a disagreement is fixed in `keys`,
  not absorbed by the oracle. Follows directly from the user's standing goal that everything `keys`
  prints must be what kitty actually does.
- **R2.5 experiment shape (D-09):** golden-output diff with the restatement lines present vs removed
  plus an in-code category table, recorded under `tmp/h<NN>-<slug>/` with a binary verdict. The
  baseline must be captured after the sequence fix, or the duplicate lines pollute the diff.
- **macOS halves (D-07/D-10):** matrix rows and the experiment's macOS re-run are labelled
  unverified-until-Phase-10 rather than presented as observed.

## Deferred Ideas

- **Acting on the R2.5 verdict** — Phase 4.
- **macOS verification** of the matrix, experiment and `cmd+k` attribution — Phase 10.
- **`keys` column alignment** (`ctrl+shift+kp_subtract` overflows its column) — cosmetic; Phase 8
  unless a plan here already edits `render_text`.
- **`[CONFLICT: also defined in <file>]` wording** differing from the frozen spec — keep the code's
  wording; Phase 8 aligns any doc quoting it.
