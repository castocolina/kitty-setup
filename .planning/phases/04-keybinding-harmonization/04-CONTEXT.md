# Phase 4: Keybinding Harmonization - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the shipped chord set kitty-organic on each OS — ctrl+shift on Linux, cmd on macOS where
kitty defines cmd chords — keeping only payload lines that earn their place (new action, behaviour
change, or a conflict with a chord our helper owns), each justified in the allow-list. Every change
is judged by the Phase 3 oracle, which must be green after each one.

Consumes, does not re-derive: the Phase 3 chord matrix (`docs/research/kitty-default-chords.md`)
and the recorded R2.5 verdict. Linux is verified here; the macOS half stays a documented hypothesis
until Phase 10, which owns fixing whatever it finds there (R7.4).

</domain>

<decisions>
## Implementation Decisions

### Per-OS mechanism
- **D-01:** Generalise the existing installer-side variant selector. `config_updater._select_clear_variant`
  becomes a per-category selector: the repo ships `<category>-linux.conf` / `<category>-mac.conf`,
  and install renames the host-matching variant to `<category>.conf` (the name `kitty-setup.conf`
  includes) and removes the other. Rationale: it is the proven pattern in this codebase, and
  `my-kitty keys` then sees only the host's lines — which the oracle requires (R2.8c, OS-correct
  default set). — **Reversibility:** reversible — install-time file selection.
- **D-02:** A single shared file binding both OSes' chords is **incorrect**, not merely inelegant:
  kitty parses `cmd+k` and `super+k` to the same chord (`mods=8`, verified in the Phase 3
  discussion), so one file binding both would self-collide on Linux. This is why D-01 is a
  correctness requirement. Rejected also: a kitty-side conditional include — unverified that kitty
  supports an OS conditional in `include`, and D-01 already works.
- **D-03:** Only categories that actually differ get variants. The Phase 3 matrix names them;
  today that is `clear` (already split) plus `windowing` (per D-04). Categories with identical
  chords on both OSes stay single-file — do not split pre-emptively.

### R2.3 — cwd inheritance
- **D-04:** On macOS, override **whichever of `cmd+t` / `cmd+n` / `cmd+enter` and
  `ctrl+shift+t` / `ctrl+shift+n` / `ctrl+shift+enter` kitty actually binds**, so the same action
  behaves identically whichever chord the user reaches for. The matrix decides which of those exist
  in kitty ≥0.49 on macOS; only chords kitty really binds get a line — no speculative bindings.
  Linux keeps `ctrl+shift+t/n/enter`. Rejected: cmd-only, which would leave the ctrl+shift variants
  silently non-inheriting and make one action behave two ways.

### kitty_mod pin
- **D-05:** The `kitty_mod ctrl+shift` pin in `kitty-setup.conf` is an **open item the matrix
  answers**, not a decision to make now. Reading so far: kitty 0.49's option definitions appear to
  default `kitty_mod` to `ctrl+shift` on both OSes, which would make the pin a no-op and the
  neighbouring comment ("macOS defaults to cmd") wrong. If the matrix confirms that, drop the pin
  and the comment; if it does not, keep the pin with corrected rationale. Either way the comment
  cannot survive unchanged.

### Allow-list
- **D-06:** Keep **one** `intentional-overrides.conf`, with OS-tagged entries where an override is
  per-OS (e.g. `cmd+k  # macOS: overrides clear_terminal to_cursor`). The introspection module
  already strips inline comments per line (`binding_introspection.py:196-209`), so tagging needs no
  parser change. Rejected: per-OS allow-list variants — doubles the files and hides half the
  justifications from any given host, when the point of the file is to be read.
- **D-07:** The `cmd+k` entry's text must change: it currently claims "macOS: new chord; no kitty
  default", which the Phase 3 research contradicts (kitty's macOS default for `cmd+k` is
  `clear_terminal to_cursor`). It becomes a declared override with that action named, per R2.4.
  Entries for chords that revert to kitty defaults are removed, per the R2.5 verdict.

### Instant clear (R2.4)
- **D-08:** Chords and semantics are already locked by earlier phases (`super+k` Linux, `cmd+k`
  macOS as a declared override, `ctrl+shift+alt+k` fallback on both, wiping screen **and**
  scrollback). What this phase adds: the ≤200 ms budget is asserted by an integration test against
  a real kitty session, not by inspection, and the fallback chord is tested as a first-class path
  rather than documented — it exists precisely for the case where a compositor grabs `super+k`.

### Oracle discipline
- **D-09:** The Phase 3 oracle runs after **every** binding change in this phase, not once at the
  end, so a regression is attributable to the change that caused it. A plan that leaves the oracle
  red does not seal, and the `keys`-derived counts in `doctor`'s expected output move in the same
  plan as the payload change that shifts them.

### Claude's Discretion
- Naming of the generalised selector and whether variant selection is table-driven or per-category.
- Whether the per-OS chord set documentation (R2.6) lives in the matrix from Phase 3 or in a
  user-facing doc — as long as one of them is authoritative and the other points at it.
- How the ≤200 ms budget is measured (wall-clock around the remote-control call vs screen-content
  polling), provided the method is recorded.
- Plan decomposition under `granularity: fine`, subject to D-09.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase inputs (produced by Phase 3 — read these first)
- `docs/research/kitty-default-chords.md` — the Linux-vs-macOS chord matrix and the per-line
  classification (new / behaviour-override / redundant restatement). This phase implements what it
  says; it does not re-derive it.
- The recorded R2.5 verdict under `tmp/h<NN>-<slug>/` — decides whether the redundant restatement
  lines in `tab-nav.conf`, `window-nav.conf`, `font-zoom.conf`, `url-hints.conf` may be deleted.
- The R2.8 oracle test — the acceptance gate (D-09).

### Requirements and plan
- `.planning/REQUIREMENTS.md` R2.1, R2.3, R2.4, R2.6, R2.7 (and R2.8 as the standing gate).
- `.planning/ROADMAP.md` "Phase 4" + "Universal Phase Gate".
- `.planning/phases/03-keybinding-research-oracle/03-CONTEXT.md` — kitty internals already
  established (sequence `.rest`, empty `definition_location`, `cmd+k` ≡ `super+k`), so they are not
  re-investigated here.

### Files this phase edits
- `config/kitty/windowing.conf` (+ its new per-OS variants), `clear-linux.conf`, `clear-mac.conf`,
  `tab-nav.conf`, `window-nav.conf`, `font-zoom.conf`, `url-hints.conf`, `layout.conf`,
  `intentional-overrides.conf`, `kitty-setup.conf` (include list and the `kitty_mod` pin).
- `src/kitty_setup/config_updater.py:21-49,240` — the variant selector being generalised (D-01).
- `tests/integration/test_h01_cwd.py`, `test_h02_clear.py`, `test_h11*`–`test_h19*` — the binding
  tests whose expectations move with the payload.

### Process
- `docs/agent-iteration.md` — every behaviour change needs a recorded experiment.
- `.claude/conventions.md` — ruff, black, pyright, bandit, vulture.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config_updater._select_clear_variant` (`:21-49`, called at `:240`) is the working prototype for
  D-01 — generalising it is a rename plus a loop, not a new subsystem.
- `intentional-overrides.conf` already documents its own format and is comment-tolerant, so D-06
  needs no parser work.
- The per-category file-basename→section convention in `my-kitty keys` means a new variant file must
  keep the category name after renaming, or grouping changes silently.

### Established Patterns
- Payload files carry their rationale as a header comment citing the change that introduced them.
  Those headers currently cite `openspec/changes/...` paths, which Phase 1 moved — when this phase
  edits a file's header, point it at `.planning/` instead of leaving a dead path.
- Redundant rebinds are detected by same-(chord, action) equality and need no allow-list entry;
  only semantic overrides do.

### Integration Points
- `doctor`'s bindings check reports `<N> ours, <M> defaults, 0 conflicts` — both counts move when
  payload lines are added or removed, and again after the Phase 3 sequence fix. Keep expectations in
  the same plan as the change.
- `layout.conf` pins `enabled_layouts` including `tall:mirrored=true`; `ctrl+shift+l` cycling depends
  on that list, and instant clear's ≤200 ms budget is unaffected by it. Do not reorder the list while
  harmonising chords — it is load-bearing for Phase 2 §11 behaviour.

</code_context>

<specifics>
## Specific Ideas

- The user's framing, carried from the Phase 1 discussion: respect kitty's organic chords unless
  they conflict with something our helper owns. Customisations exist to add behaviour, not to
  re-letter kitty.
- The instant-clear divergence is deliberate and is the one chord that differs by OS, because it
  matches each host's iTerm-style convention.

</specifics>

<deferred>
## Deferred Ideas

- **macOS verification** of every criterion here — Phase 10, which may also fix what it finds (R7.4).
- **Scene chords** (R5.3's chord→scene mapping) — Phase 7; R2.7 only verifies that
  `ctrl+shift+alt+c` and the existing custom chords are free, it does not bind scene chords.
- **`ctrl+shift+alt+c`** itself — Phase 6 binds it; this phase only confirms the chord is
  unclaimed on both OSes.
- **Repro-doc rewrites** for every chord that moves — Phase 8 owns doc accuracy, but a chord changed
  here must not leave a repro doc asserting the old behaviour; note it rather than silently skipping.

</deferred>

---

*Phase: 4-Keybinding Harmonization*
*Context gathered: 2026-09-22*
