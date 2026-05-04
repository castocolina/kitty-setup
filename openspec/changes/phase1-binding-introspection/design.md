## Context

Phase 1 §3 of `docs/requirements.md` calls for binding introspection so a user
can see, in one command, every chord that kitty will respond to and which of
those chords is in conflict. The bootstrap change shipped six bindings and the
absence of this feature already cost us once: Probe 04 revealed that
`ctrl+shift+-` shadows kitty's default `change_font_size all -2.0`, a regression
nobody caught.

We have to enumerate from the *parsed* kitty config (so what we report is what
the user actually gets), and we have to attribute each binding to its source
file (so the report is grouped, not a flat 70-entry list). The probe pass
established two non-obvious facts about how to do this on kitty 0.46:

* No `kitten @ list-keys` exists (Probe 01); the only structured exit is via
  `kitty +runpy` and `kitty.config.load_config`.
* `KeyDefinition.definition_location` is unusable after parse (Probe 03);
  source-file attribution must come from a separate, manual pass over our
  own config files.

## Goals / Non-Goals

**Goals:**
- A `kitty-setup-bindings` CLI that prints every active binding, grouped by
  source file, with conflicts flagged. Default output is plain text suitable
  for a terminal; `--json` emits machine-readable output for tests and future
  doctor consumers.
- A doctor check that reports `bindings: <N> ours, <N> defaults, <N> conflicts`
  and FAILs when any of our bindings collide with a non-default binding (i.e.
  with another binding from our payload, indicating an internal conflict, OR
  with a kitty default that we did NOT explicitly intend to shadow).
- An integration test that drives the introspection module against a scratch
  config dir (via a pytest fixture), without requiring a live `KittySession`,
  and asserts the report shape and the expected conflict set.
- Categorisation convention documented in `docs/agent-iteration.md`: file
  basename in `config/kitty/` = category in the report.

**Non-Goals:**
- Fixing the `ctrl+shift+-` collision. Follow-up change.
- Surfacing bindings outside the default keyboard mode (sequence keymaps,
  custom modes). Phase 1 §3 talks about "every active binding"; the default
  mode is what almost every user touches. Custom modes are deferred until
  someone actually defines one.
- Mouse bindings (`mousemap`). Same reasoning — defer until needed.
- A GUI / kitten-side report. Phase 3 packaging concern.

## Decisions

### D1 — Enumerate via `kitty +runpy`, not via shell-out to a CLI helper

**Why:** Probe 01 showed kitty has no built-in `list-keys`-style command. Probe
02 showed `kitty.config.load_config` returns a complete keymap structure that
we can walk in one round trip. Calling `kitty +runpy <script> <conf-path>` is
the cheapest stable path; the script we send is small (≤ 30 lines) and emits
JSON to stdout.

**Alternative considered:** parse our config files ourselves and re-implement
kitty's `map` resolver. Rejected — re-implementing kitty's binding parser is
guaranteed to drift from kitty's actual behavior, which is the entire thing
the report is supposed to reflect.

### D2 — Source-file attribution comes from a manual pre-walk of our payload

**Why:** Probe 03 showed `KeyDefinition.definition_location` is empty after
parse. We own the installed payload files (`payload_dir`, i.e. `~/.config/kitty/kitty-setup/`);
we can scan them for `^\s*map\s+(\S+)\s+(.+)$` ourselves and build a
`(chord_string, action_string) -> source_file` map. We then cross-reference this
against the parsed keymap from D1 to attribute each binding to a file. Anything
in the parsed keymap that we did NOT author gets labelled `kitty-default`.

**Alternative considered:** monkey-patch `CurrentlyParsing` to capture file
context per definition. Rejected — fragile, kitty-version-coupled, more code
than the manual pre-walk.

### D3 — Conflict = chord with `len(defs) > 1` AND not "our intentional default override"

**Why:** Probe 04 showed kitty preserves every `map` line in `defs[]`. A naïve
"any chord with multiple defs is a conflict" report would flag four of our
bootstrap bindings (we deliberately replaced `new_tab` / `new_window` /
`new_os_window` / `scroll_line_up` with cwd-inheriting equivalents). Those are
*intentional* overrides.

We distinguish:

* **Intentional override** — the chord has exactly two defs (one kitty default
  + one of ours), AND the chord string is present in the allow-list
  (`config/kitty/intentional-overrides.conf`). Both conditions must hold.
* **Real conflict** — any other multi-def case. Formally: `len(defs) > 1 AND NOT
  (len(defs) == 2 AND chord_string in allow_list)`. This means:
  - Our binding shadows a kitty default that is NOT in the allow-list → conflict.
  - Two of our bindings target the same chord (even if the chord is in the allow-list) → conflict.
  - Three or more defs for any chord, regardless of allow-list → conflict.
  Any real conflict FAILs the doctor check.

The allow-list is short by design — the bootstrap change has 4 entries
(`ctrl+shift+t`, `ctrl+shift+n`, `ctrl+shift+enter`, `ctrl+shift+k`).
`ctrl+shift+-` will NOT be in the allow-list, so the report will FAIL on this
install until the follow-up change moves the horizontal-split chord off it.

### D4 — Output shape: grouped plain text by default, JSON behind `--json`

**Why:** doctor consumes JSON; humans read text. One CLI, two formats. Plain
text default keeps `kitty-setup-bindings` useful at a glance.

CLI flags:
- `--json` — emit machine-readable JSON instead of plain text.
- `--config-path <path>` — path to the kitty config file to load. Defaults to
  `~/.config/kitty/kitty.conf` when omitted.

Default-resolution for parameters not exposed as flags (used internally by `main()` and
by the doctor check):
- `kitty_bin` — discovered via `shutil.which("kitty")`; if that returns `None`, falls
  back to `installer.SYMLINK_PATH` and then `installer._kitty_bin(installer.DEFAULT_DEST)`
  in that order (same candidate list as `_check_kitty_binary()` in `doctor.py`). If no
  candidate resolves, `enumerate()` raises `BindingIntrospectionError` and `main()` exits
  non-zero with a descriptive message.
- `payload_dir` — defaults to `~/.config/kitty/kitty-setup/` (i.e.
  `config_updater.ConfigPaths.for_user().payload_dir`).
- `allow_list` — defaults to `payload_dir / "intentional-overrides.conf"`.

Plain-text shape:

```
windowing (5 bindings)
  ctrl+shift+t       launch --type=tab --cwd=current        [overrides default new_tab]
  ctrl+shift+n       launch --type=os-window --cwd=current  [overrides default new_os_window]
  ctrl+shift+enter   launch --location=after --cwd=current  [overrides default new_window]
  ctrl+shift+\       launch --location=vsplit --cwd=current
  ctrl+shift+-       launch --location=hsplit --cwd=current  [CONFLICT: kitty default change_font_size all -2.0]

bindings (1 binding)
  ctrl+shift+k       combine : clear_terminal scrollback active : send_text … \x0c  [overrides default scroll_line_up]

kitty defaults (64 bindings)
  ctrl+shift+c       copy_to_clipboard
  ctrl+shift+v       paste_from_clipboard
  ...

Summary: 5 ours, 64 defaults, 1 conflict.
```

JSON shape: list of `{chord, action, source, override_of, conflicts_with}` records
plus a `summary` block.

### D5 — Doctor check exits non-zero only on REAL conflicts

**Why:** intentional overrides are healthy; flagging them as failures would
make doctor permanently red. The new check exits FAIL only when at least one
real conflict exists.

### D6 — Hypothesis lives in `tmp/h03-introspection/`

**Why:** R1 still applies — the report shape and conflict-detection logic land
there first, exercised against a real install via the harness, and only then
get promoted to `src/`, `tests/integration/`, and `docs/repro/`. The probes
took us from "can we read this at all" to "yes via `+runpy`"; the hypothesis
takes us from "we can read it" to "the report we want is correct".

## Risks / Trade-offs

* **Risk: kitty internals (Options shape, `keyboard_modes[""].keymap`) change in a future kitty release.** → *Mitigation:* the `+runpy` snippet is small and pinned in source; a future kitty bump would surface a clear failure mode in the integration test, and re-probing is cheap. Kitty has been stable here across recent versions, but we don't promise forward compatibility.
* **Risk: chord representation gap — kitty stores `SingleKey(mods=int, key=int)` as integers; we want `ctrl+shift+t` strings in the report.** → *Mitigation:* `KeyDefinition.human_repr()` produces a printable form (confirmed in Probe 02's enumerated `def attrs` list). Use `human_repr()` rather than reverse-mapping integers. Note: the probe's narrative also mentions `pretty_repr()`, but `pretty_repr` does not appear in Probe 02's enumerated attribute list (which was truncated to `[:8]` alphabetically); its existence is unconfirmed. Do not rely on `pretty_repr()` until the hypothesis verifies it.
* **Risk: the allow-list (`intentional-overrides.conf`) drifts from the real overrides, creating noise.** → *Mitigation:* the file is short, sits next to the bindings it allows, and changes only when bindings change. Reviewer-enforced; CI later.
* **Trade-off: D2's manual config-file pre-walk only attributes OUR bindings (the ones we wrote). Kitty defaults are a single bucket, no per-component grouping.** Acceptable for now — the user's primary question is "what does my install do?", and the answer "5 of these are ours, here's where each lives, the other 64 are kitty defaults" is sufficient.

## Migration Plan

This is an additive change. No existing behavior changes; no migration required.

Deploy:

1. Land the new module + tests + doctor check.
2. Run `make doctor`. If the conflict count is zero, ship. If it is non-zero
   (which it WILL be for the `ctrl+shift+-` collision), the doctor check FAILs
   and a follow-up change is required to fix the binding before we can call
   `doctor` healthy on this branch.

   Decision for THIS change: ship the introspection capability and accept the
   doctor regression, since the regression is the one we want the introspection
   to surface. Reverting to ship a green doctor would mean withholding the very
   feature that found the bug. The follow-up change lands within the same PR
   stack.

Rollback:

1. Revert the four commits. The doctor check goes away. The intentional-overrides
   file goes away. The Python module goes away. The `[project.scripts]` entry
   goes away. No persistent state was created anywhere.

## Open Questions

* **Q1 — Do we want chord normalisation?** `ctrl+shift+t` and `kitty_mod+t`
  (when `kitty_mod = ctrl+shift`) refer to the same chord. The report should
  probably normalise to one canonical form. *Decision:* yes, normalise to
  the explicit-modifier form (`ctrl+shift+t`) in the report. Implement in the
  hypothesis.
* **Q2 — Should the allow-list live in `config/kitty/` or in `src/`?** Putting
  it next to `windowing.conf` and `bindings.conf` keeps the "intention vs
  collision" question in one directory; putting it in `src/` keeps the kitty
  config payload pure config. *Decision:* `config/kitty/intentional-overrides.conf`
  — same directory as the bindings it justifies. The introspection module
  reads it at run time, NOT through kitty's parser (it is not kitty-config
  syntax).
