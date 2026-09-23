# Phase 3: Keybinding Research & Oracle - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the instrument before touching the subject. This phase delivers (a) the R2.8 oracle test
that can prove `my-kitty keys` truthful, (b) the chord matrix research deliverable, (c) the
recorded R2.5 verdict on whether redundant payload lines can go, and (d) the R1.8 chord
normalisation the oracle's attribution work depends on. **No chord is added, removed, or rebound
in this phase** — that is Phase 4, judged by what is built here.

Two truthfulness bugs found during this discussion ARE in scope, because the oracle cannot pass
while they exist: sequence flattening (D-02) and the `keys` fixes that follow from it.

</domain>

<decisions>
## Implementation Decisions

### R2.8 — the oracle
- **D-01:** The oracle's independent source of truth is **kitty's own renderer**: call kitty's
  `debug_config` / `ShortcutMap` code through `kitty +runpy` and parse what *kitty* formats, rather
  than re-walking `opts.keyboard_modes[""].keymap` with our own modifier arithmetic. Rationale: it
  is the only candidate that would have caught both bugs found in this discussion, because the
  chord strings come from kitty, not from us. Verified available in kitty 0.49: `kitty.debug_config`
  exports `debug_config`, `print_mapping_changes`, `compare_maps`, `mod_to_names`, `ShortcutMap`.
  Rejected: a second hand-written snippet (same mechanism, same blind spots) and a committed golden
  file (catches our drift, not kitty's, and rots on every kitty upgrade). — **Reversibility:**
  costly — the oracle is the acceptance gate for Phases 4, 7 and 10; replacing its source later
  means re-proving every binding change made against it.
- **D-02:** **Sequence bindings are rendered as full sequences** (`ctrl+shift+p > f`), built from
  `KeyDefinition.rest`. This fixes a pre-existing truthfulness bug found here: the keymap dict key
  is only the *prefix* chord, and the current snippet drops `.rest`, so `my-kitty keys` prints
  `ctrl+shift+p` 10 times with 10 different actions and `ctrl+shift+a` 4 times — exactly the
  phantom/duplicate class R2.8(d) forbids. Empirically, only 2 chords are affected in kitty 0.49's
  defaults (`p`, `a`); total definitions are 101, matching today's 22 ours + 79 defaults. Rejected:
  prefix-with-count (hides what the sequences do) and omitting sequences (hides bindings that can
  collide with ours).
- **D-03:** **The oracle asserts chord + action 1:1; it does NOT assert source.** kitty cannot tell
  us origin — `definition_location.filename` is empty for all 101 definitions (re-verified this
  discussion, confirming the original probe), which is why `_walk_payload` exists at all.
  Attribution correctness is proven instead by **targeted tests over known fixtures**: a chord only
  our payload defines, a pure kitty default, a redundant rebind, and a line in the user's
  `kitty.conf` outside our block. ROADMAP criterion 1 is reworded from "chord, action, and source"
  to match. Rejected: having the oracle reconstruct expected source from the payload files — that
  re-implements the code under test inside the test, so a shared misunderstanding passes both.
- **D-04:** Strictness: exact equality, no tolerance list. When the oracle and `keys` disagree, the
  fix goes in `keys` (or in the payload), never in the oracle. If a divergence is ever judged
  legitimate, it is recorded as a decision with its rationale, not silently allow-listed.
- **D-05:** The oracle runs against a **real kitty session built by the existing harness**
  (`KittySession`, `KITTI_INTEGRATION=1`) using the installed config, so it exercises the same
  include chain a user gets.

### R1.8 — chord normalisation
- **D-06:** Payload chord strings are normalised through **kitty's own `parse_shortcut`** in the
  same runpy call, and compared in parsed form. This makes `cmd+k` ≡ `super+k` by construction
  (verified: both parse to `mods=8, key_name='k'`) and covers every alias kitty accepts — `cmd`,
  `opt`, glyph forms — without us maintaining a table. Rejected: a Python alias table, which would
  have to track kitty's alias list forever. Note the payload walk already depends on kitty for the
  keymap, so this adds a round trip, not a new dependency.

### R2.2 — chord matrix research
- **D-07:** `docs/research/kitty-default-chords.md` is sourced from kitty's own introspection first
  and its docs second — where the two disagree, introspection wins and the disagreement is noted.
  macOS rows come from kitty's source/docs (`is_macos` branches in the option definitions) and are
  labelled **unverified-until-Phase-10**, never presented as observed.
- **D-08:** The matrix classifies every current payload line as new / behaviour-override / redundant
  restatement, which is the input Phase 4 consumes. It must also record the two macOS facts already
  established: kitty's macOS default `cmd+k` is `clear_terminal to_cursor` (so our instant-clear is
  a real override there, contradicting today's `intentional-overrides.conf` comment), and
  `ctrl+shift+j`/`k` are `scroll_line_*` **smooth** in kitty ≥0.47.

### R2.5 — categorisation experiment
- **D-09:** The experiment is a **golden-output comparison** under `tmp/h<NN>-<slug>/`: capture
  `my-kitty keys` output with the redundant restatement lines present, then with them removed plus
  an in-code action→category table, and diff. The verdict is binary and recorded either way —
  identical grouping means Phase 4 may delete the lines; any difference means they stay, with the
  reason written down. Per D-02 the baseline must be captured *after* the sequence fix, or the diff
  is polluted by the duplicate lines.
- **D-10:** The experiment's macOS half cannot run here (no Mac). It is recorded as Linux-verified
  with the macOS re-run assigned to Phase 10, matching how R2.5's "verified on Bazzite and macOS"
  wording is satisfied across the two phases.

### Claude's Discretion
- Whether the `keys` JSON gains explicit fields for sequence/shadowed state, or encodes them in the
  chord string alone (D-02).
- How the `debug_config` output is parsed (dedicated parser module vs inline in the test) and
  whether the oracle lives in `tests/integration/` only or gains a reusable helper.
- The hypothesis directory numbering (next free `h<NN>`) and how the experiment's artefacts are laid
  out inside it.
- Plan decomposition under `granularity: fine`, provided the oracle lands before anything it judges.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase intent and requirements
- `.planning/REQUIREMENTS.md` R2.8 (five truthfulness properties a–e), R2.2, R2.5, R1.8.
- `.planning/ROADMAP.md` "Phase 3" + "Universal Phase Gate" — criterion 1 is reworded per D-03.
- `.planning/phases/01-governance-freeze/01-CONTEXT.md` — mantra, `AGENTS.md` canonical rules, git
  model, tooling discipline, CodeGraph lifecycle.
- `.planning/phases/02-defect-remediation/02-CONTEXT.md` — Phase 2 fixes this phase builds on;
  note R1.8 was explicitly deferred from Phase 2 to here.

### Code under test
- `src/kitty_setup/binding_introspection.py:42-62` (`_RUNPY_SNIPPET` — the source of the sequence
  bug), `:152-173` (`_run_kitty_runpy`), `:178-193` (`_walk_payload` — attribution), `:196-209`
  (allow-list), `:86-136` (`render_text` / `to_json`), `:333-354` (`enumerate_bindings`).
- `src/kitty_setup/doctor.py:101-118` (`_check_bindings` — consumes the same report).
- `src/kitty_setup/harness/kitty_session.py` — `KittySession`, the vehicle for D-05.
- `config/kitty/*.conf` — the payload whose lines the matrix classifies;
  `config/kitty/intentional-overrides.conf` — the allow-list, including the `cmd+k` comment D-08
  contradicts.

### Process
- `docs/agent-iteration.md` — hypothesis/probe discipline for D-09.
- `.claude/conventions.md` — ruff, black, pyright, bandit, vulture.

### Kitty internals established this discussion (no need to re-derive)
- `opts.keyboard_modes[""].keymap` keys on the **prefix** `SingleKey`; `KeyDefinition.rest` holds
  the remainder of a sequence; `is_sequence`, `human_repr()`, `pretty_repr()`,
  `full_key_sequence_to_trigger` are available.
- `definition_location.filename` is empty for all 101 definitions — attribution cannot come from kitty.
- `kitty.debug_config` exports `debug_config`, `ShortcutMap`, `compare_maps`, `mod_to_names`.
- `parse_shortcut('cmd+k')` and `parse_shortcut('super+k')` both give `mods=8, key_name='k'`.
- `kitty --debug-config` is **not** a CLI flag (it is a mappable action) — any doc or message
  claiming otherwise is wrong; Phase 2 D-09 fixes the doctor label.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_run_kitty_runpy` already handles the runpy invocation, JSON parsing, and error wrapping — the
  oracle's kitty call and the D-06 normalisation round trip can reuse that shape.
- `Binding` / `Report` dataclasses already carry `source`, `override_of`, `conflicts_with`,
  `redundant`; sequence/shadowed state can extend them rather than replacing the model.
- `KittySession` harness + `KITTI_INTEGRATION=1` gating is the established way to get a real kitty.
- `tests/unit/test_binding_introspection.py` already fixtures payload dirs — the D-03 attribution
  tests extend that pattern instead of inventing one.

### Established Patterns
- Probe findings are recorded as code comments citing the probe id (`binding_introspection.py:37,
  176, 212`). The two findings from this discussion belong there too.
- The introspection module shells out to kitty and never imports it — keep that boundary; the oracle
  is a test, so it may drive kitty directly.

### Integration Points
- `doctor`'s bindings check consumes `enumerate_bindings`, so a chord-string change from D-02 shifts
  doctor's counts (`22 ours, 79 defaults` today) — update the expected values and any test asserting
  them in the same plan, not a later one.
- `my-kitty keys` output is user-facing; D-02 changes what a user sees, so the repro/docs that quote
  it need the same treatment (Phase 8 owns doc accuracy, but do not leave a quoted example wrong).

</code_context>

<specifics>
## Specific Ideas

- The user's standing goal for this phase, restated from the Phase 1 discussion: everything
  `my-kitty keys` prints must be what kitty actually does — past contradictions came from `keys`
  listing things that did not exist or were not effective. The sequence bug is a concrete instance.
- Build the instrument first: the oracle must be green before Phase 4 changes a single chord.

</specifics>

<deferred>
## Deferred Ideas

- **Removing the redundant restatement lines** — Phase 4 acts on the D-09 verdict; this phase only
  produces it.
- **macOS verification** of the matrix, the categorisation experiment, and the `cmd+k` attribution —
  Phase 10 (R7.4 allows fixing what it finds there).
- **`keys` column alignment** (`ctrl+shift+kp_subtract` overflows the 22-char column, so its action
  runs into the chord) — cosmetic, surfaced in the audit; fix only if a plan here already touches
  `render_text`, otherwise Phase 8.
- **`[CONFLICT: also defined in <file>]` wording** differing from the frozen spec's text — the spec
  is history now; keep the code's wording and let Phase 8 align any doc that quotes it.

</deferred>

---

*Phase: 3-Keybinding Research & Oracle*
*Context gathered: 2026-09-22*
