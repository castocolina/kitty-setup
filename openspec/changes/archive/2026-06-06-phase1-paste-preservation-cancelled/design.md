## Context

Phase 1 §4 of `docs/requirements.md` asks for: "Paste preserves CLI output exactly — no trailing spaces on copied lines (regression vs iTerm)." User-confirmed (2026-05-07) that the load-bearing pain is `\` line-continuations being broken by kitty's trailing-whitespace padding on copy: the backslash is no longer immediately followed by a newline, so the shell stops treating the next line as a continuation. Manifestation: pasting a copied multi-line `make` / `docker run` / `git` / `curl` command into a fresh shell yields incomplete or erroring executions. Left-side indentation issues exist but are secondary and explicitly out of scope for this change. iTerm on macOS does NOT pad — it strips trailing whitespace per-line on copy, which is the behaviour to match.

Foundation in place from `phase1-curated-bindings` (archived 2026-05-07): kitty 0.46.2 install, `make doctor` reports `bindings: 24 ours, 79 defaults, 0 conflicts`, surgical install/uninstall, hypothesis-driven workflow proven.

## Goals / Non-Goals

**Goals:**

* Characterise the cause of the trailing-whitespace regression with named probes (R6).
* Ship the smallest config-only remediation that resolves it on Linux first; document the macOS variant.
* Capture the behavioural contract as the new `kitty-paste-preservation` capability so a future regression breaks `make doctor` / `make test`, not the user's daily workflow.
* Stay strictly inside config land — no kitten, no helper script, no vendored runtime dependency. Roadmap rule: "scripts first, kitten last."

**Non-Goals:**

* Image-paste (Phase 1 §7) — separate change.
* tmux config shipping — kitty-setup does not own user tmux config; tmux-side guidance lives in the repro doc only if config-only kitty fix is insufficient.
* Wayland-vs-X11 cross-compositor portability work — verify on the host's compositor; document gaps.
* Per-OS divergent solutions — prefer one config that works on both Linux and macOS. Acceptable to defer macOS to a follow-up if the Linux fix doesn't translate cleanly.

## Decisions

### D1: Probe-first, three named external-system probes before any config change

Per `docs/agent-iteration.md` R6, every external-system assumption gets a probe in `tmp/probes/phase1-paste-preservation/`. Three planned up front:

* **probe-01: which kitty 0.46.x settings affect paste content?** — list every kitty `paste_actions`, `strip_trailing_spaces` (if exists), `clipboard_control`, and adjacent setting via `kitty --debug-config` or kitty docs. Verdict: which knobs (if any) control trailing whitespace on paste.
* **probe-02: is the trailing whitespace introduced on copy or on paste?** — drive `KittySession`, type a known short line, exercise both copy paths (`kitten @ get-text`, mouse-select-driven kitty clipboard), inspect the bytes that landed in the system clipboard. Verdict: source of the regression — kitty's renderer-padding-on-copy vs paste-time reflow.
* **probe-03: does tmux `set-clipboard` rewrite the selection before kitty sees it?** — if the user runs tmux, capture the clipboard with and without tmux in the loop. Verdict: tmux's contribution (or non-contribution) to the regression.

Each probe writes its verdict + the design decision or code path that uses it.

### D2: Single hypothesis under `tmp/h17-paste-preservation/`

One hypothesis dir, one autonomous probe. The probe drives `KittySession` to:

1. Type a known multi-line shell command using `\` line-continuations (e.g. `make build \\\n    --target=foo\n`) plus a clean-line case (`echo hello\n`) plus a worst-case multi-line block (a 5-line `docker run` invocation).
2. Capture the active window's text via `kitten @ get-text --extent=all` (`KittySession.get_text()`).
3. Assert each backslash is immediately followed by `\n` (no whitespace inserted between them) and clean lines have no inserted trailing whitespace.

If the autonomous probe reproduces the regression on Linux, iterate `draft.conf` until the bytes match. If the autonomous probe does NOT reproduce it (the regression is mouse-select-only, not `get-text`-driven), the autonomous coverage is limited to behaviour we can verify; the manual repro carries the rest, exercising real mouse-select copy + paste into a fresh `bash` window and asserting the multi-line command runs cleanly.

### D3: Promote based on probe verdict

Three branches, picked at promotion time:

* **Branch (a) — kitty config fix.** If probe-01 surfaces a knob that resolves the regression, ship it in a new `config/kitty/paste.conf` with one `include` line in `kitty-setup.conf`. File-basename = category convention applies. No `intentional-overrides.conf` entries unless a chord is bound (likely none for paste-actions; this is a non-chord category).
* **Branch (b) — tmux-side documentation.** If probe-03 surfaces tmux's `set-clipboard` as the cause and kitty cannot work around it via config, the remediation is a paragraph in `docs/repro/h17-paste-preservation.md` instructing users to set `set -g set-clipboard external` (or equivalent) in their `~/.tmux.conf`. We don't ship the tmux config; we document the gap. The repro doc's `## Known limitations` section is the user-facing fix.
* **Branch (c) — out-of-tree helper.** If neither (a) nor (b) is sufficient (e.g. the regression is in the X11 vs Wayland clipboard MIME-type plumbing), document the helper-shaped workaround in the repro doc without shipping a script in this change. A future change can promote it if dogfooding shows the helper is load-bearing.

### D4: Capability shape — `kitty-paste-preservation`

The new capability is a single behavioural contract: "copying N bytes from a kitty window and pasting them into a fresh shell yields N bytes back, modulo bracketed-paste markers." Two scenarios:

1. **Lines with trailing whitespace are preserved verbatim.** Typing `"a line with two trailing spaces  \n"` and copying it back yields `"a line with two trailing spaces  "` (no insertion, no truncation).
2. **Lines without trailing whitespace stay clean.** Typing `"a clean line\n"` and copying it back yields `"a clean line"` (no inserted whitespace).

Backing the spec: the autonomous probe in `tmp/h17-paste-preservation/run.py` plus the integration test promoted from it.

## Risks / Trade-offs

* **Risk:** Cause turns out to be Wayland clipboard MIME plumbing, neither kitty nor tmux fault. → **Mitigation:** Branch (c) — document the workaround, scope a follow-up change if the helper becomes load-bearing during dogfooding.
* **Risk:** macOS doesn't reproduce the bug, or reproduces it via a different mechanism. → **Mitigation:** Linux-first per spec; macOS deferred-with-note. The hypothesis includes `## macOS Status` capture; if reproduction differs, the follow-up `phase1-paste-preservation-macos` is named and tracked.
* **Risk:** kitty's `paste_actions` is a single-knob switch and its modes have behavioural side effects beyond trailing-whitespace handling. → **Mitigation:** probe-01 documents every mode; the design decision picks the most-narrow effective setting.
* **Risk:** The autonomous probe via `KittySession.get_text()` doesn't exercise the same code path as a real mouse-select copy. → **Mitigation:** call this out in the repro doc explicitly; manual repro on a real session is the load-bearing verification for the mouse-select path.

## Open Questions

1. **Does kitty 0.46.x have `strip_trailing_spaces` or equivalent?** Resolved by probe-01: yes — `strip_trailing_spaces` exists with values `never` (default) / `smart` / `always`. `smart` is the narrow remediation.
2. **Is the regression bracketed-paste-marker-related?** If kitty defaults to bracketed paste and the trailing-whitespace appears INSIDE the markers, the user's downstream consumer (shell, editor) might be the actual culprit. Resolve by inspecting clipboard bytes vs paste-receiving-buffer bytes separately.
3. **Does macOS reproduce under tmux?** User-reported "yes" but verify with a probe before committing to a fix. (tmux probe deferred — tmux not installed on the probe host.)
4. **Should the remediation also cover paste IN to kitty?** Spec says "preserves CLI output" — covering the copy direction is sufficient. Defer paste-in changes to a follow-up if needed.

## Probes

External-system probes per R6 (`docs/agent-iteration.md`). Artefacts under
`tmp/probes/phase1-paste-preservation/`; findings encoded below and durable
through this design doc.

| # | Slug                                | Verdict                    | Decision informed |
|---|-------------------------------------|----------------------------|-------------------|
| 01 | `kitty-paste-knobs`                | holds                      | D3 branch (a) — `strip_trailing_spaces` is the knob. Default `never` reproduces; `smart` is the narrow fix (preserves intentional trailing whitespace in rectangle selections), `always` is the broad fix. Confirms no `paste_actions` / `clipboard_control` mode is needed. |
| 02 | `where-trailing-ws-comes-from`     | fails (assumption refuted) | D3 branch (a) test shape. Padding is NOT in the logical line buffer (`kitten @ get-text` extents `all`/`screen` show backslash immediately followed by newline). The regression is purely on the renderer→clipboard serialisation path. The integration test must read the actual clipboard bytes (via `wl-paste`/`xclip`), not just `get_text()`. |
| 03 | `tmux-set-clipboard`               | partial-with-workaround    | D3 branch (a) confirmed sufficient on the kitty side: with `strip_trailing_spaces=smart`, `copy_last_command_output` round-trips intentional 3-trailing-space content verbatim through the system clipboard. The tmux-side variant could not be exercised (tmux not installed on the probe host); follow-up work under D3 branch (b) documents the tmux `set-clipboard` guidance in the repro doc once a tmux-equipped host verifies it. |

Implication for the §2 hypothesis: `tmp/h17-paste-preservation/draft.conf`
starts at `strip_trailing_spaces smart`, the autonomous probe drives a
`KittySession` with `shell bash` + `shell_integration enabled` (NOT
`--noprofile --norc`) so `copy_last_command_output` works, asserts on
`wl-paste` (Wayland) / `xclip -selection clipboard -o` (X11) bytes, and
documents the mouse-select path in the repro doc as manual-repro-only.
