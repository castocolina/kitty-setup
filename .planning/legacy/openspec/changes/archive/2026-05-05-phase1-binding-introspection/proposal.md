## Why

Phase 1 §3 of `docs/requirements.md` asks for an introspection command that lists every active binding grouped by category, so conflicts are visible *before* they bite. Probe 04 just demonstrated why this matters: the live bootstrap install has five chord collisions where our config shadows kitty defaults, four intentional and one — `ctrl+shift+-` overriding `change_font_size all -2.0` — a silent regression we shipped without noticing. A user who tries the default font-zoom-out chord today will get a horizontal split instead of smaller text. An introspection command would have flagged the collision the first time `make doctor` ran.

## What Changes

- Add a `keys` subcommand to the existing `my-kitty` CLI (`my-kitty keys`) that lists every active binding from a real kitty config load. Output groups bindings by source file (our payload — `windowing.conf`, `bindings.conf`, etc. — plus a "kitty defaults" bucket for everything else). Each entry shows the chord, the action, and a flag when the chord is in conflict with another definition.
- Wire the same enumeration into `make doctor`: a new check `bindings: <N> ours, <N> defaults, <N> conflicts` that turns FAIL when any of our bindings collide with anything other than the kitty default the binding was meant to replace.
- Document the categorisation convention in `docs/agent-iteration.md`: file basename = category. Existing payload files (`windowing.conf`, `bindings.conf`) already follow it.
- Out of scope here, but blocked-on-this-change: a follow-up change `fix-ctrl-shift-minus-collision` to move the horizontal-split chord off `ctrl+shift+-`. That change will use the new introspection command as its verification gate.

## Capabilities

### New Capabilities

- `kitty-binding-introspection`: enumerate every binding active in a given kitty config, group by source file, surface conflicts. Delivered as a Python module wired into the existing `my-kitty` CLI as a `keys` subcommand, plus a doctor-integrated summary check. Backed by an integration test that loads the live `~/.config/kitty/kitty.conf` and asserts the report shape.

### Modified Capabilities

- `kitty-install`: doctor gains a new check (`bindings`). The existing six checks (kitty binary / symlink / desktop entry / payload / sentinel block / parse) are unchanged; this adds a seventh that reports binding counts and exits non-zero on unexpected conflicts.
- `my-kitty-cli`: the "Single binary on PATH with subcommand dispatch" requirement gains `keys` as a sixth supported subcommand alongside `install`, `uninstall`, `doctor`, `prune`, and `help`. No new entry point — this is a subcommand register inside the existing `cli.py` dispatcher.

## Probes

- [`tmp/probes/phase1-binding-introspection/01-no-builtin-list-keys.md`](../../tmp/probes/phase1-binding-introspection/01-no-builtin-list-keys.md) — `kitten @ list-keys` / `kitty +list-bindings` do not exist. Verdict: **fails**. Implies: no shell-out option; we go through `kitty +runpy`.
- [`tmp/probes/phase1-binding-introspection/02-runpy-keymap-shape.md`](../../tmp/probes/phase1-binding-introspection/02-runpy-keymap-shape.md) — `kitty.config.load_config` returns `Options.keyboard_modes[""].keymap` as a `dict[SingleKey, list[KeyDefinition]]`. Verdict: **holds**. Implies: D1 below.
- [`tmp/probes/phase1-binding-introspection/03-definition-location-unreliable.md`](../../tmp/probes/phase1-binding-introspection/03-definition-location-unreliable.md) — `KeyDefinition.definition_location` is empty after parse (kitty reuses one shared `CurrentlyParsing` object that gets reset). Verdict: **fails — workaround**. Implies: D2 below (parse our own files manually for source attribution).
- [`tmp/probes/phase1-binding-introspection/04-conflict-as-multiple-defs.md`](../../tmp/probes/phase1-binding-introspection/04-conflict-as-multiple-defs.md) — duplicate `map` directives produce multiple `KeyDefinition` entries in `defs[]`. Verdict: **holds**. Implies: D3 below (conflict detection is `len(defs) > 1`). Bonus: 5 collisions present in current install.

## Impact

- **New top-level paths**: `src/kitty_setup/binding_introspection.py`, `tests/unit/test_binding_introspection.py`, `tests/integration/test_h03_introspection.py`, `docs/repro/h03-introspection.md`.
- **Edited files**: `src/kitty_setup/cli.py` (register the `keys` subparser dispatching to the new module), `src/kitty_setup/doctor.py` (new check), `docs/agent-iteration.md` (file-basename = category convention). No new `[project.scripts]` entry — `keys` is a subcommand of the existing `my-kitty` binary, dispatched by `cli.py`. No new Makefile target this round; users invoke `my-kitty keys` directly.
- **System mutations**: none. The introspection command is read-only — it loads the user's kitty config and prints a report.
- **Out of scope**: fixing the discovered `ctrl+shift+-` collision. The follow-up change `fix-ctrl-shift-minus-collision` will own that.
