## Context

Phase 1 §5 of `docs/requirements.md` calls for a curated keybinding set with six categories: tab nav, window/split nav (vim h/j/k/l), font zoom, detach, broadcast, URL hints — identical on Linux and macOS. The foundation already ships:

* cwd-inheriting tab/window/split *creators* in `config/kitty/windowing.conf` (5 chords: `ctrl+shift+t`, `n`, `enter`, `\\`, `-`).
* instant-clear in `config/kitty/bindings.conf` (1 chord: `ctrl+shift+k`).
* `intentional-overrides.conf` allow-list metadata (read by `my-kitty keys` and the doctor `bindings` check).
* `my-kitty keys` introspection grouped by file-basename category.

Two latent collisions surface as soon as §5 chords are planned:

1. `ctrl+shift+k` is currently instant-clear, but vim convention puts "focus up" on `k`. §5 lists vim `h/j/k/l` as a hard requirement.
2. `ctrl+shift+-` is currently `launch --location=hsplit --cwd=current` (in `windowing.conf`), but kitty's default for that chord is `change_font_size all -2.0`. §5 lists font zoom as a hard requirement. The archived `phase1-binding-introspection` proposal already flagged this collision and named a follow-up change `fix-ctrl-shift-minus-collision`; that follow-up folds into this change.

## Goals / Non-Goals

**Goals:**

* Ship six chord categories covering every §5 sub-requirement (tab nav, window nav with vim h/j/k/l, font zoom, detach, broadcast, URL hints).
* Pin `kitty_mod ctrl+shift` so the same literal chord works on Linux and macOS — no `cmd` remap, no per-OS divergence.
* One `.conf` file per category so `my-kitty keys` reports each category as its own section (file-basename = category convention).
* One hypothesis per subgroup under `tmp/h<NN>-bindings-<subgroup>/`, each with an autonomous integration probe + a manual repro doc.
* Resolve the two collisions above as a side-effect of the change. After merge, `make doctor` reports `0 conflicts` and `my-kitty keys` reports every shadow as `[overrides default <action>]`.

**Non-Goals:**

* Phase 1 §4 paste preservation, §6 suspend/monitor survival, §7 image-paste parity. Each is its own change.
* Phase 2 scenes layer.
* A full rebind of every kitty default. Only the categories listed in §5 are touched. Defaults outside the curated set keep working as kitty ships them.
* Per-OS chord variants. macOS-only `cmd+*` overrides (e.g. iTerm `cmd+k` parity) are explicitly deferred to a follow-up change so this one stays Linux-first.
* Modes / chord sequences (e.g. `ctrl+shift+space` leader). Single-chord bindings only.

## Decisions

### D1: Pin `kitty_mod ctrl+shift` once, in `kitty-setup.conf`

Kitty defaults `kitty_mod` to `ctrl+shift` on Linux and `cmd` on macOS. Without an explicit pin, the same `kitty_mod+t` directive resolves to two different physical chords across OSes. Pinning `kitty_mod ctrl+shift` in the managed entry makes the chords identical literal strings on both platforms. We also author every curated `map` line in **explicit-modifier form** (`ctrl+shift+<key>`, never `kitty_mod+<key>`) so the chord is unambiguous when read in source and by `my-kitty keys`.

**Alternative considered:** keep kitty's per-OS default modifier and produce per-OS bindings files. Rejected: doubles the spec surface, doubles repro effort, and breaks the §5 "identical bindings on Linux and macOS" requirement at the source.

### D2: One file per category, file-basename = category

The introspection tool already groups bindings by source file. Splitting bindings into `tab-nav.conf`, `window-nav.conf`, `font-zoom.conf`, `detach.conf`, `broadcast.conf`, `url-hints.conf` makes the catalog self-documenting at the filesystem level. Existing `bindings.conf` is renamed to `clear.conf` so the same convention applies to instant-clear (one category, one file).

**Alternative considered:** keep all curated bindings in one fat `bindings.conf`. Rejected: defeats the "categories visible at a glance" property of `my-kitty keys`, and contradicts the file-basename = category convention documented in `docs/agent-iteration.md`.

### D3: Move instant-clear off `ctrl+shift+k`; new chord is `ctrl+shift+l` reserved for window-nav-right ⇒ instant-clear lands on `ctrl+shift+x`

`k` must be free for vim window-nav-up. Candidate replacements: `x`, `;`, `escape`, `delete`. Chosen: **`ctrl+shift+x`**. Reasons:

* `x` is unbound in default kitty.
* Easy single-key reach from home row, paired mnemonically with "exit/erase".
* Does not collide with the curated set (no `x` chord planned in any category).
* Does not collide with kitty's `paste_from_clipboard` default (`ctrl+shift+v`) or `cut`-style conventions.

`ctrl+shift+x` SHALL still be allow-listed in `intentional-overrides.conf` only if it shadows a kitty default (it does not in current kitty versions, but the tool will flag it if a future version adds one).

**Alternative considered:** keep `ctrl+shift+k` for instant-clear, use arrow keys for window-nav. Rejected: §5 explicitly names vim `h/j/k/l` as the hard requirement.

### D4: Move horizontal-split off `ctrl+shift+-`; new chord is `ctrl+shift+_` (i.e. `ctrl+shift+shift+minus`, written canonically)

Required to free `ctrl+shift+-` for the kitty-default `change_font_size all -2.0`. Candidate replacements for hsplit: `ctrl+shift+/`, `ctrl+shift+_`, `ctrl+shift+;`. Chosen: **`ctrl+shift+/`**. Reasons:

* Symmetric with `ctrl+shift+\\` already in use for vsplit (visual mirror — forward-slash for horizontal divider, backslash for vertical).
* `/` is unbound in default kitty.
* Single key, no shift-of-shift ambiguity.

This is an edit to `config/kitty/windowing.conf`; the cwd-inheritance *behavior* is unchanged (the spec doesn't pin the chord). `intentional-overrides.conf` loses its `ctrl+shift+-` entry (the chord goes back to its kitty default and our binding no longer exists).

**Alternative considered:** keep hsplit on `ctrl+shift+-` and reassign font-zoom-out to `ctrl+shift+0` (with reset on a different chord). Rejected: kitty default is the well-known parity expectation, and `ctrl+shift+0` is the obvious chord for "reset" not "decrease".

### D5: Re-bind kitty defaults under our category files; allow-list each in `intentional-overrides.conf`

For chords that already do the right thing under kitty defaults (e.g. `ctrl+shift+]` = `next_tab`), authoring an explicit `map` line in our category file produces a duplicate definition. The current introspection rule `len(defs) > 1` flags this as a conflict. The intentional-overrides allow-list resolves it: list the chord with reason "redundant binding for `<category>.conf` categorisation".

**Why redundant binding at all:** the `kitty-curated-bindings` requirement "Each category appears as its own section in the binding report" needs the binding to live in the category file. Without an explicit `map` line, the chord stays under `kitty defaults` in `my-kitty keys` and the user can't see it grouped with the rest of tab-nav.

**Alternative considered:** extend the introspection module to recognize same-action redefinitions as overrides (not conflicts). Rejected for *this* change as scope creep — would need a delta on `kitty-binding-introspection`. Tracked as a follow-up if the allow-list grows beyond ~10 lines and the noise becomes a maintenance cost.

**Update 2026-05-06:** the alternative-rejected above was wrong on the facts. Allow-list-only resolution provably cannot resolve same-action shadows: (a) the conflict rule "two of ours target the same chord" fires *before* the allow-list check, and (b) kitty's parser returns the upstream default and our redundant rebind as two distinct entries in `defs[]` with identical `(chord, action)`. The naive `payload_map` lookup therefore double-attributed both entries to "ours", and the conflict rule then flagged the chord regardless of allow-list membership. The introspection module DID need a small dedupe in `_classify` (≈13 lines) to attribute each `(chord, action)` to our payload at most once. That change shipped here. The behavioral change is tracked formally via a delta on `kitty-binding-introspection` under `openspec/changes/phase1-curated-bindings/specs/kitty-binding-introspection/spec.md`.

### D6: Concrete chord allocation (subject to repro)

| Category    | Chord                | Action                                              | Source        |
| ----------- | -------------------- | --------------------------------------------------- | ------------- |
| tab-nav     | `ctrl+shift+]`       | `next_tab`                                          | replaces kitty default `next_window` (h11 probe finding) |
| tab-nav     | `ctrl+shift+[`       | `previous_tab`                                      | replaces kitty default `previous_window` (h11 probe finding) |
| tab-nav     | `ctrl+shift+.`       | `move_tab_forward`                                  | kitty default |
| tab-nav     | `ctrl+shift+,`       | `move_tab_backward`                                 | kitty default |
| tab-nav     | `ctrl+shift+q`       | `close_tab`                                         | kitty default |
| window-nav  | `ctrl+shift+h`       | `neighboring_window left`                           | replaces kitty default `show_scrollback` (h12 probe finding — D6 originally said "new") |
| window-nav  | `ctrl+shift+j`       | `neighboring_window down`                           | replaces kitty default `scroll_line_down` (h12 probe finding — D6 originally said "new") |
| window-nav  | `ctrl+shift+k`       | `neighboring_window up`                             | replaces kitty default `scroll_line_up` (h12 probe finding — D6 originally said "new (was clear)"; the kitty default re-emerged once §1 moved instant-clear to ctrl+shift+x) |
| window-nav  | `ctrl+shift+l`       | `neighboring_window right`                          | replaces kitty default `next_layout` (h12 probe finding — D6 originally said "new") |
| window-nav  | `ctrl+shift+w`       | `close_window`                                      | kitty default (redundant rebind for categorisation) |
| window-nav  | `ctrl+shift+f`       | `next_window`                                       | replaces kitty default `move_window_forward` (h12 probe finding — D6 originally said "new") |
| font-zoom   | `ctrl+shift+=`       | `change_font_size all +2.0`                         | kitty default (redundant rebind for categorisation) |
| font-zoom   | `ctrl+shift+-`       | `change_font_size all -2.0`                         | kitty default (redundant rebind for categorisation; freed by §2 hsplit relocation) |
| font-zoom   | `ctrl+shift+0`       | `change_font_size all 0`                            | replaces kitty default `tenth_window` (h13 probe finding — D6 originally said "kitty default"; kitty 0.46.x binds font-reset on `ctrl+shift+backspace` instead) |
| detach      | `ctrl+shift+d`       | `detach_window ask`                                 | new (h14 probe finding — kitty 0.46.x has no default on the chord; D6 prediction "new" confirmed) |
| detach      | `ctrl+shift+alt+d`   | `detach_tab ask`                                    | new (h14 probe finding — kitty 0.46.x has no default on the chord; D6 prediction "new" confirmed) |
| broadcast   | `ctrl+shift+i`       | `launch --allow-remote-control kitty +kitten broadcast` | new (h15 probe finding — kitty 0.46.x has no default on the chord; D6 prediction "new" confirmed. Action string updated to the form documented in kitty's broadcast kitten manual; the original D6 listing `kitten broadcast.py` is a working alias from older kitty versions but the upstream-doc form is more stable.) |
| url-hints   | `ctrl+shift+e`       | `open_url_with_hints`                               | kitty default |
| clear       | `ctrl+shift+x`       | `combine : clear_terminal scrollback active : send_text normal,application \\x0c` | new (was on `k`) |

windowing.conf change:

* `ctrl+shift+\\` → vsplit (unchanged).
* `ctrl+shift+/` → hsplit (was `ctrl+shift+-`).

`intentional-overrides.conf` after the change:

* `ctrl+shift+t`, `ctrl+shift+n`, `ctrl+shift+enter` — windowing creators (unchanged).
* `ctrl+shift+]`, `ctrl+shift+[`, `ctrl+shift+.`, `ctrl+shift+,`, `ctrl+shift+q` — tab-nav. Three (`.`, `,`, `q`) are redundant rebinds of kitty defaults; two (`]`, `[`) replace kitty's window-nav defaults with the matching tab-nav action (vim-style window-nav lands on `hjkl` in §4).
* `ctrl+shift+h`, `ctrl+shift+j`, `ctrl+shift+k`, `ctrl+shift+l`, `ctrl+shift+f` — window-nav. Replace kitty defaults `show_scrollback` / `scroll_line_down` / `scroll_line_up` / `next_layout` / `move_window_forward` with vim-style `neighboring_window` motions and round-robin `next_window` (h12 probe finding — D6 originally classed these as "new"; the probe found per-chord defaults).
* `ctrl+shift+w` — window-nav close (kitty default same action; rebound for categorisation).
* `ctrl+shift+=`, `ctrl+shift+-` — font-zoom, redundant rebinds of kitty defaults. `ctrl+shift+0` — font-zoom, replaces kitty default `tenth_window` with `change_font_size all 0` (h13 probe finding — D6 originally classed all three as redundant rebinds; the probe found `0` defaults to `tenth_window` and reset is on `ctrl+shift+backspace`).
* `ctrl+shift+e` — url-hints, redundant rebind of kitty default.
* (detach: nothing) — `ctrl+shift+d` and `ctrl+shift+alt+d` are genuinely new in kitty 0.46.x (h14 probe finding, 2026-05-06); neither shadows a kitty default, so neither needs an allow-list entry. First §-category in this change where allow-list rows are unchanged.
* (broadcast: nothing) — `ctrl+shift+i` is genuinely new in kitty 0.46.x (h15 probe finding, 2026-05-06); chord is unbound by default, so it needs no allow-list entry. Second §-category in this change where allow-list rows are unchanged (same precedent as §6 detach).

Deletions vs current allow-list:

* `ctrl+shift+k` — moves out (no longer instant-clear; `ctrl+shift+k` is now `neighboring_window up`, not a shadow because kitty has no default on `ctrl+shift+k` outside our config).

### D7: Hypothesis layout per subgroup

Following the iteration pattern in `docs/agent-iteration.md` (one hypothesis per behavior):

```
tmp/h09-bindings-clear-relocation/   # instant-clear chord move (ctrl+shift+k → ctrl+shift+x)
tmp/h10-bindings-hsplit-relocation/  # ctrl+shift+- → ctrl+shift+/
tmp/h11-bindings-tab-nav/            # Renumbered from h03 — h03 is taken by binding-introspection (test_h03_introspection.py).
tmp/h12-bindings-window-nav/         # Renumbered from h04 to keep h<NN> integers contiguous after h09/h10/h11.
tmp/h13-bindings-font-zoom/          # Renumbered from h05 per the h11/h12 precedent — h<NN> integers stay contiguous.
tmp/h14-bindings-detach/             # Renumbered from h06 per the h11/h12/h13 precedent — h<NN> integers stay contiguous.
tmp/h15-bindings-broadcast/          # Renumbered from h07 per the h11/h12/h13/h14 precedent — h<NN> integers stay contiguous.
tmp/h16-bindings-url-hints/          # Renumbered from h08 per the h11/h12/h13/h14/h15 precedent — h<NN> integers stay contiguous.
```

Numbering picks up after the existing h01 (cwd) and h02 (clear). Each dir contains: `01-<probe-name>.md` notes, an integration test under `tests/integration/test_h<NN>_bindings_<subgroup>.py`, and a `docs/repro/h<NN>-bindings-<subgroup>.md` manual doc with `## Linux Status` and `## macOS Status` sections.

## Risks / Trade-offs

* **Risk:** `intentional-overrides.conf` bloats with ~10+ lines of "redundant binding for categorisation". → **Mitigation:** D5's deferred follow-up. If the file grows past 15 lines, file a change to extend introspection to recognize same-action redefinitions as non-conflicts.
* **Risk:** The hsplit chord move (`ctrl+shift+-` → `ctrl+shift+/`) is a user-visible behavior change. Anyone who already installed and habituated to `ctrl+shift+-` for hsplit will be surprised. → **Mitigation:** call out in the change's release note (commit body) and update README quickstart.
* **Risk:** `change_font_size` requires a kitty version that supports it on the user's installed font. → **Mitigation:** existing `make doctor` already loads the parsed config; the integration probe asserts the action is registered and the chord is unique. Visual zoom is part of the manual repro, not the autonomous probe.
* **Risk:** `kitten broadcast.py` is a kitty kitten path that may differ across kitty versions / install layouts. → **Mitigation:** the broadcast hypothesis (h15) ran its own probe; the upstream-documented form `launch --allow-remote-control kitty +kitten broadcast` parses cleanly on kitty 0.46.2 and the kitten ships with the install (probe 2026-05-06). If the kitten path becomes unstable in a future kitty version, fall back to a remote-control-driven `send-text --match` shell-out — the `kitty-curated-bindings` spec deliberately leaves the broadcast action string unconstrained for this reason.
* **Risk:** macOS-deferred subgroups linger forever as `deferred`. → **Mitigation:** the `Linux-first delivery, macOS-deferred-with-note` requirement explicitly prevents declaring §5 closed until every subgroup is `verified` on macOS.
* **Risk:** Doctor surface drift — adding 10+ chords could push the existing `bindings: <N> ours` line past readable width. → **Mitigation:** doctor already prints counts; format is unchanged.

## Open Questions

1. **Broadcast mechanism** — is `kitten broadcast.py` reliable enough to bind directly, or do we need a custom remote-control script? ~~Resolve in h07 probe.~~ **Resolved (h15 probe, 2026-05-06):** kitty's official broadcast kitten ships in 0.46.x and is invokable as `kitty +kitten broadcast` (the form documented in kitty's own broadcast kitten manual). All three candidate action strings — `launch --allow-remote-control kitty +kitten broadcast`, `launch --allow-remote-control kitten broadcast`, `launch --allow-remote-control kitten broadcast.py` — parse cleanly through `binding_introspection.enumerate_bindings`. **Chosen action:** `launch --allow-remote-control kitty +kitten broadcast` for upstream-doc parity (most stable surface; matches what a user would type at a shell). The custom remote-control script alternative was not needed — the official kitten works on the live install. Behavioural confirmation that typing in the broadcast window mirrors to siblings is gated on the manual repro (`docs/repro/h15-bindings-broadcast.md`) — kitty remote control's `send-key` cannot drive interactive input.
2. **Detach prompt** — `detach_window ask` and `detach_tab ask` open kitty's interactive picker. ~~If that UX is ugly, we may swap to `detach_window new-tab` (no prompt).~~ **Resolved (h14 probe, 2026-05-06):** both `ask` variants parse cleanly via kitty's binding introspection. The `ask` variants align directly with the §6 spec wording "kitty-supported equivalent that prompts the user for target", so we bind them as listed in D6. Behavioural confirmation of the picker UX lives in `docs/repro/h14-bindings-detach.md` (manual repro) — kitty remote control's `send-key` cannot drive an interactive picker, so this is gated on the manual repro by design (same precedent as §4/§5).
3. **macOS-only iTerm-parity overrides** — should `cmd+k` (clear), `cmd+t`, `cmd+w`, `cmd+]`, `cmd+[` be added on macOS only via a separate include? Out of scope for this change. **Status (2026-05-06): tracked as a follow-up change `phase1-curated-bindings-macos-overrides`** — to be filed once the Linux catalog is dogfooded for at least one cycle. No work in this change; the `kitty_mod ctrl+shift` pin (D1) means the curated chords already work as-is on macOS, just without the iTerm muscle-memory parity layer.
4. **Renaming `bindings.conf` → `clear.conf`** — does the doctor's existing `bindings` check name need to follow the rename? **Resolved (sanity sweep, 2026-05-06):** the check name `bindings` in `src/kitty_setup/doctor.py:_check_bindings` is the doctor section name, not the file name. It maps to the catalog-wide invariant "ours vs defaults vs conflicts" reported by `binding_introspection.enumerate_bindings()`, not to any one source file. No rename required. `make doctor` still reports `PASS bindings: 24 ours, 79 defaults, 0 conflicts` after the rename.
5. **Broadcast scope vs spec wording** — the `kitty-curated-bindings` spec preamble talks about "broadcast across all windows in the active tab", but the kitten launched by `ctrl+shift+i` (`launch --allow-remote-control kitty +kitten broadcast`) mirrors typed input to **all kitty windows** by default, not just the active tab. **Status (2026-05-06): leave as-is, document in catalog table, flag as a follow-up.** Rationale: (a) the spec deliberately leaves the broadcast action string unconstrained (Risks/Trade-offs entry on the broadcast kitten); (b) tightening the action string with `--match-tab state:focused` (or whatever the correct selector is for kitty 0.46.x) needs its own probe — changing the action string mid-archive is risk we don't need to take when the loose interpretation is spec-conformant; (c) the broader behaviour is arguably more useful for the dogfooding phase ("broadcast to everything I'm running"). Tracked as **`phase1-curated-bindings-broadcast-tab-scope`** for a follow-up change after dogfooding; if the wider scope turns out to be the desired behaviour, the spec preamble can be reworded to match instead.
