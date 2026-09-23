# Phase 6: Pane Color Cycle - Context

**Gathered:** 2026-09-22
**Status:** Ready for planning

<domain>
## Phase Boundary

One keypress (`ctrl+shift+alt+c`) rotates the focused pane's background **and** its tab accent to
the next palette entry, statelessly — the pane's current colour *is* the state. Adds
`my-kitty window cycle-color` as the shell-equivalent of the chord, and an editable palette file
seeded copy-if-absent next to scenes.

Delivers R4.1–R4.4. Does **not** add presets or chord→scene mapping (Phase 7), does not change what
`my-kitty window background` / `my-kitty tab accent` do, and does not verify anything on macOS
(Phase 10).

</domain>

<decisions>
## Implementation Decisions

### Scouting facts established before the questions (do not re-derive)
- **All nine palette entries already resolve** through `normalize_color` — measured, not assumed:
  `blue→#0000ff`, `green→#00ff00`, `red→#ff0000`, `yellow→#ffff00`, `purple→#a020f0`,
  `teal→#008080`, `orange→#ffa500`, `gray→#bebebe`, `none→NONE`. No colour-table work is needed.
- **The latency target is not a constraint.** `kitten` is a Go binary spawning in ~10 ms (measured
  3×) and `my-kitty --help` runs in ~45 ms (measured 3×). A press costs at most
  `get-colors` + `set-colors` + `set-tab-color` plus one CLI start — an order of magnitude under the
  300 ms target. No mechanism needs to be chosen *for speed*.
- **`kitten @ get-colors` accepts `--match`**, so the focused pane's background is directly
  readable (verified against the installed kitten's own help).

### The `none` slot (R4.3)
- **D-01:** Keep R4.3 as written — **any background not matching a palette entry advances to the
  first entry**. A reset pane and a never-cycled pane therefore behave identically, which is the
  correct semantics rather than a defect: both are "not currently on the wheel", and both should go
  to `blue`. Consequence accepted: the `none` slot is not distinguishable from "fresh" by
  inspection.
- **D-02:** The one **real** failure mode gets handled explicitly: if the user's *configured*
  default background equals a palette entry's hex, that entry becomes unreachable and the cycle
  silently skips it. Detect the collision and surface it (a `doctor` note or a warning on the
  cycle path) rather than misbehaving quietly. This is the R2.8 principle applied outside `keys` —
  the tool does not report or imply something that is not happening.
- **D-03:** Before any comparison logic is built, **an experiment pins down `get-colors`' exact
  output format** for (a) a pane with a set background and (b) a pane just reset with `NONE` —
  including whether the value comes back as `#rrggbb`, a bare hex, or a name. The matching rule is
  written against observed output, per R0.1. Comparison is on **normalised** values
  (`normalize_color` applied to palette entries) so `blue` and `#0000ff` are the same position.

### Tab accent scope (R4.1)
- **D-04:** The chord **always sets both** the pane background and the tab accent —
  **last-write-wins** when a tab holds several panes. R4.1 words it as an unconditional pair, and
  `set-tab-color` is inherently tab-scoped (kitty has no per-pane tab accent), so some pane must
  win; the most recently cycled one is the predictable choice.
  Rejected: a solo-tab guard reusing `launcher._origin_tab_is_solo` (`launcher.py:175`). That check
  exists to protect a **destructive** decision — piling new windows onto a populated tab, where
  being wrong loses layout. Recolouring is non-destructive and instantly re-triggerable, so the
  fail-safe buys little and would make one chord behave two ways depending on how many panes a tab
  happens to hold — the same "one action, two behaviours" problem rejected in Phase 4 D-04.
  Also rejected: a `--no-tab` flag, which adds CLI surface for a chord-driven feature nobody asked
  to split.

### Palette file (R4.2)
- **D-05:** The palette is **TOML** at `$XDG_CONFIG_HOME/kitty-setup/palette.toml` (fallback
  `~/.config/`), beside `scenes/` — resolved the same way `recipe.scenes_dir()` resolves
  (`recipe.py:46`), and seeded **copy-if-absent** using `seed_scenes()`'s existing contract so a
  user-edited palette is never overwritten. Default contents are the nine entries in R4.2's order.
  Rationale for TOML over a plain `.conf`: Phase 7 (R5.1) already puts presets in user TOML, so
  choosing line-based here would either force a second format or contort presets later. One
  format, one loader (`tomllib`), one error path.
- **D-06:** Entries are validated through `normalize_color` **at load time**, and an invalid entry
  is a clear error naming the file, the entry, and the line — not a silent skip and not a crash
  mid-cycle. An empty or missing palette falls back to the built-in default order rather than
  failing the chord, since the chord has no place to show a parse error.

### Chord invocation (R4.4)
- **D-07:** The chord is a `launch --type=background` map line invoking
  **`my-kitty window cycle-color`** — the real CLI. This is the only option where the chord and the
  shell command are *provably the same behaviour*, which is what makes success criterion 1 testable
  at all, and it is what R4.1's "exactly the existing behaviours" requires.
  Rejected: `remote_control_script` (fastest, but a second implementation of the cycle living inside
  kitty's runtime, outside the existing harness) and a static `map … remote_control set-colors …`
  (impossible — choosing the next colour requires reading the current one).
- **D-08:** **Open item for the experiment, not an assumption:** whether `KITTY_WINDOW_ID` and
  socket resolution reach a `--type=background` launch. Grounds for expecting yes:
  `launcher._origin_window()` (`launcher.py:163`) already reads `KITTY_WINDOW_ID` from the
  environment, and Phase 2's R1.6 exists *because* that variable leaks into test environments — so
  propagation is real; the untested part is specifically the `background` launch type. If it does
  not propagate, the fallback is `--match id:@active-kitty-window-id` style selection resolved
  inside the CLI, decided by the same experiment. Plans must not hard-code either until it is run.

### Claude's Discretion
- Whether the cycle logic lives in a new `scenes/cycle.py` or extends `background.py`, and the
  internal signature of the next-colour function.
- `--reverse` / `--match` / `--to` plumbing details; whether `--to` reuses `_resolve_socket`
  unchanged (it should) and how `--match` composes with the focused-window default.
- How the ≤300 ms assertion is measured, given it is not a binding constraint — a single
  wall-clock assertion around the CLI call is sufficient; recording the method is what matters.
- Where the D-02 collision warning surfaces (`doctor` check vs cycle-path warning vs both).
- Plan decomposition under `granularity: fine`, and the one-commit-per-plan rule (Phase 1 D-16).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and plan
- `.planning/REQUIREMENTS.md` — R4.1, R4.2, R4.3, R4.4.
- `.planning/ROADMAP.md` "Phase 6" + "Universal Phase Gate".

### Prior phase context (decisions not to re-derive)
- `.planning/phases/01-governance-freeze/01-CONTEXT.md` — the research→experiment→decide mantra
  (D-01), tooling discipline (D-12), one-commit-per-plan (D-16).
- `.planning/phases/04-keybinding-harmonization/04-CONTEXT.md` — `ctrl+shift+alt+c` is confirmed
  unclaimed on both OSes there; this phase binds it. Also the source of the "one action must not
  behave two ways" principle cited in D-04.
- `.planning/phases/05-component-separation-version-floor/05-CONTEXT.md` — the payload now splits
  into `foundation/` and `scenes/` subdirectories (D-01), so **the new chord's `map` line belongs
  under `scenes/`**, not at the payload root: it depends on remote control, which is scenes-owned
  (D-02 there). The allow-list stays at the payload root (D-05 there).

### Code this phase builds on
- `src/kitty_setup/scenes/colors.py:64` — `normalize_color`, the single validation and
  name→hex resolution point (R4.2, D-06).
- `src/kitty_setup/scenes/background.py:18` — `set_window_background`, reused verbatim.
- `src/kitty_setup/scenes/accent.py:18` — `set_tab_accent`, reused verbatim (sets `active_bg` and
  `inactive_bg` together).
- `src/kitty_setup/scenes/_client.py:107` — `kitten_at`; `:81-105` `_resolve_socket` for `--to` and
  multi-instance disambiguation.
- `src/kitty_setup/scenes/launcher.py:163` — `_origin_window()`, the `KITTY_WINDOW_ID` precedent
  for D-08; `:175` `_origin_tab_is_solo`, the precedent deliberately **not** reused (D-04).
- `src/kitty_setup/scenes/recipe.py:46` — `scenes_dir()`, the XDG resolution `palette.toml` mirrors.
- `src/kitty_setup/installer.py:88-113` — `seed_scenes()`'s copy-if-absent contract, reused for
  seeding the palette (D-05).

### Process
- `docs/agent-iteration.md` — the D-03 and D-08 experiments are required, not optional.
- `.claude/conventions.md` — ruff, black, pyright, bandit, vulture.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `set_window_background` and `set_tab_accent` are already single-purpose, already normalise their
  input, and already fail-soft by printing kitten's stderr and returning its exit code. The cycle
  is a *composition* of these two plus one read — no new remote-control surface.
- `color_completer` (`colors.py:91`) exists for `<color>` arguments; `cycle-color --to`/`--match`
  need no new completer, but a palette-aware completer is a cheap follow-on if wanted.
- `_client.kitten_at` centralises socket resolution, so multi-instance disambiguation (criterion 4)
  is inherited rather than implemented.
- `tests/integration/_kitty_subprocess.py` already has a `get_color` helper (`:140`) — the read side
  of this feature has a test harness already.

### Established Patterns
- Colour handling is **client-side first**: normalise and reject before any `kitten @` call, so a
  bad value never half-applies. The cycle must follow this — validate the whole palette at load,
  not per press.
- Scene primitives are `<verb>.py` modules with a `set_*` function plus a thin `cli_*` handler that
  catches `ColorError` and `SceneClientError` and returns 1. A new cycle module follows that shape.
- `fail-soft` is the house style for multi-step remote-control operations (`_apply_bg`,
  `_fail_soft` in `launcher.py`): print stderr, record the first non-zero exit, never raise
  mid-sequence. The two-call pane+tab update should behave the same way — a failed tab accent must
  not leave the user unsure whether the background changed.

### Integration Points
- **Phase 5 ordering.** The chord's `map` line and any new payload file land under `scenes/` per
  Phase 5 D-01/D-02. If Phase 6 were planned before Phase 5 executes, the file location would be
  wrong; the dependency is real.
- **The Phase 3 oracle** is the standing R2.8 gate: adding a chord changes `my-kitty keys` output
  and `doctor`'s `<N> ours` count. Both move in the same plan as the `map` line, and the oracle
  must be green after it.
- **`intentional-overrides.conf`** needs no entry for `ctrl+shift+alt+c` if Phase 4 confirms the
  chord is a kitty non-default (a new action needs no override justification) — but the allow-list's
  own format decides that; check it rather than assuming either way.
- **`doctor`** gains a check if D-02's collision warning lands there, which shifts its expected
  output; keep any asserting test in the same plan.

</code_context>

<specifics>
## Specific Ideas

- The user's framing from the PRD round, restated: *"imagina que aplico los mismos comandos solo que
  en lugar de eso uso un combo que rota esos colores"* — the chord is a trigger for behaviour that
  already exists, not a new colour feature. No darkening, no transformation, colours used exactly as
  named. D-07 is the structural expression of that.
- Statelessness is a feature, not a constraint to work around: no state file to go stale, and a pane
  that looks blue *is* at the blue position.

</specifics>

<deferred>
## Deferred Ideas

- **macOS verification** of the chord, the launch mechanism, and `get-colors` output — Phase 10.
- **Multiple named palettes** (switching palette sets) — TOML was chosen partly because it makes
  this possible later; not in scope now.
- **Palette-aware tab completion** for a future `--to <color>` style argument — cheap follow-on,
  not required by R4.4.
- **Per-pane opacity** — already settled as impossible in kitty (`docs/repro/h26-perpane-opacity.md`);
  not revisited.
- **Chord→scene mapping** (R5.3) and **presets** (R5.1) — Phase 7, which will reuse this phase's
  TOML loader choice.

</deferred>

---

*Phase: 6-Pane Color Cycle*
*Context gathered: 2026-09-22*
