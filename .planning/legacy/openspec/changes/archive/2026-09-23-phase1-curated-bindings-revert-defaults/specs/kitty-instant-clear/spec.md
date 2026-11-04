## MODIFIED Requirements

### Requirement: Instant-clear chord matches host-OS iTerm convention with cross-OS fallback

The chord bound to instant clear SHALL match host-OS iTerm convention: `super+k` on Linux, `cmd+k` on macOS. A secondary fallback chord, `ctrl+shift+alt+k`, SHALL also be bound to the same instant-clear action on both OSes, so a user whose compositor grabs `super+k` (or who prefers cross-OS literal parity) has a reachable alternative. The chord `ctrl+shift+x` SHALL NOT be bound to instant clear — that chord is reserved for kitty's default `scroll_to_prompt 1` shell-integration jump and is released back to kitty by this change. Vim-style chords `ctrl+shift+h`, `ctrl+shift+j`, `ctrl+shift+k`, and `ctrl+shift+l` are no longer reserved by curated navigation (see `kitty-curated-bindings`), so the historical prohibition against instant-clear landing on those chords no longer applies — but the new instant-clear chords (`super+k`, `cmd+k`, `ctrl+shift+alt+k`) are different chords regardless. Each instant-clear chord MUST satisfy the `kitty-curated-bindings` rules: authored in explicit-modifier form, allow-listed in `intentional-overrides.conf` (each is net-new — no kitty default — so the allow-list comment reads "new chord; no kitty default" rather than an override rationale), and reported under the `clear` source section by `my-kitty keys`.

#### Scenario: Linux clear chord is super+k with ctrl+shift+alt+k fallback
- **WHEN** the user runs `my-kitty keys --json` after install on Linux
- **THEN** the `clear` section lists at least two bindings: one chord `super+k`, one chord `ctrl+shift+alt+k`, both with the instant-clear action

#### Scenario: macOS clear chord is cmd+k with ctrl+shift+alt+k fallback
- **WHEN** the user runs `my-kitty keys --json` after install on macOS
- **THEN** the `clear` section lists at least two bindings: one chord `cmd+k`, one chord `ctrl+shift+alt+k`, both with the instant-clear action

#### Scenario: ctrl+shift+x is released back to scroll_to_prompt 1
- **WHEN** kitty's keymap is inspected after install
- **THEN** the chord `ctrl+shift+x` resolves to kitty's default `scroll_to_prompt 1`, and no curated binding shadows it

#### Scenario: Instant-clear behavior holds on the new chord
- **WHEN** an integration test sends 50 marker lines, then triggers the instant-clear chord (`super+k` on Linux, `cmd+k` on macOS, or the `ctrl+shift+alt+k` fallback on either OS)
- **THEN** `KittySession.get_text(extent="all")` returns text that contains none of the 50 marker lines within 200 milliseconds of the chord being sent
- **AND** the cursor remains usable for subsequent input

## REMOVED Requirements

### Requirement: Instant-clear chord does not collide with curated navigation chords

**Reason:** The premise — that `ctrl+shift+h`/`j`/`k`/`l` are reserved by curated vim-style window navigation — no longer holds. With this change those chords return to kitty defaults (`show_scrollback`, `scroll_line_down`, `scroll_line_up`, `next_layout`). The new instant-clear chord (`super+k` / `cmd+k` / `ctrl+shift+alt+k`) is on a different modifier entirely. The "Instant-clear chord matches host-OS iTerm convention with cross-OS fallback" requirement above subsumes the chord-choice contract.

**Migration:** Any consumer of this requirement should switch to the new "matches host-OS iTerm convention" requirement; the chord assertion changes from "final key is not h/j/k/l" to "chord is `super+k`, `cmd+k`, or `ctrl+shift+alt+k` per the table".
