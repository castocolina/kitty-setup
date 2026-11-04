# Design — phase2-scene-title-primitive

## Context

`phase2-remote-control-foundation` (archived 2026-05-13) shipped
`allow_remote_control yes` + `listen_on unix:/tmp/kitty` in the managed kitty
config, plus a `kitten @ ls` doctor check. The remote-control surface is
live and verifiable, but nothing in the repo *uses* it yet — every Phase 2
§8-§14 capability has been blocked on the surface existing.

Phase 2 §8 is the first scene primitive: set a kitty window or tab title to
arbitrary text (including emoji). The h22 explore (2026-05-13) verified
empirically that `kitten @ set-window-title "🐳 docker test"` round-trips
byte-faithfully through `kitten @ ls`, so the protocol-level question is
settled. What remains is the shape decision — and that shape will be copied
by §9 (accent), §10 (background), §11 (font), §12 (transparency), §13
(named scenes), §14 (chord-to-scene). The first primitive to land sets the
template for everything after.

Inputs to this design:
- `docs/requirements.md` §8 (Phase 2 scope).
- `docs/propossal_roadmap.md`: "every scene capability begins as a plain
  script driving Kitty through its remote-control socket. One script per
  hypothesis. The kitten layer is a packaging step, not a prerequisite."
- `CLAUDE.md` "Stack" rule: subcommands under
  `src/kitty_setup/cli.py`, single `[project.scripts]` entry point
  (`my-kitty`). User-clarified scope (2026-05-13): rule binds at the
  *promotion* boundary; Python hypothesis scripts under `tmp/h<NN>-<slug>/`
  are sanctioned scratch.
- Existing surface: `kitty-remote-control` capability spec and
  `src/kitty_setup/doctor.py` helpers (`_pgrep_kitty_pids`,
  `_parse_listen_on_base`).

## Goals / Non-Goals

**Goals:**

- Ship the first end-user-invokable scene primitive (set window/tab title).
- Lock the CLI surface shape (noun-first) that §9-§14 will copy.
- Establish `src/kitty_setup/scenes/` as the package home for runtime scene
  primitives.
- Encapsulate `kitten @` socket discovery in one helper so future primitives
  reuse rather than re-implement it.
- Honour the existing project rules: hypothesis-first
  (`tmp/h22-window-title/run.py`), promotion lands as a `my-kitty`
  subcommand, no shell scripts outside the bootstrap pair, autonomous
  integration tests gated behind `KITTI_INTEGRATION=1`.

**Non-Goals:**

- New autocomplete machinery. The `my-kitty-cli` capability already
  ships `argcomplete` registration in `main()` and the
  `register-python-argcomplete` eval line inside the sentinel-bracketed
  rc block. Adding subparsers `window` and `tab` inherits completion
  automatically — no new registration, no new rc-edit work.
- §9-§14 sibling primitives. Each lands as its own change once §8 is in
  place.
- Chord binding for `window title` / `tab title`. Defer to §14, where the
  named-scene-to-chord wiring lives.
- macOS verification. Tracked as deferred-with-reason follow-up
  `phase2-scene-title-primitive-macos`.
- A new doctor check. Title is a runtime primitive, not an install-time
  invariant; verifying "title can be set" tells the user nothing the
  existing `kitty-remote-control` reachability check doesn't already cover.

## Decisions

### D1: Noun-first CLI shape — `my-kitty window title <text>`

Chosen surface:

```
my-kitty window title <text> [--temporary/--no-temporary] [--match <expr>] [--to <socket>]
my-kitty tab    title <text> [--temporary/--no-temporary] [--match <expr>] [--to <socket>]
```

Alternatives considered:
- **Verb-first** (`my-kitty title window <text>`). Reads like English but
  explodes the top-level verb space when §9-§14 land: `title`, `accent`,
  `background`, `font`, `transparency`, `layout`, `scene`. Seven verbs vs
  three nouns (`window`, `tab`, `scene`).
- **Scene-only** (`my-kitty scene apply <name>`, no per-attribute
  subcommand). The roadmap's "one script per hypothesis, dogfooded
  per-primitive" rule forbids this until §13-§14 land — §8 needs to be
  invokable on its own to be hypothesis-validated.

Rationale: noun-first scales — every future primitive nests under the
relevant noun (`window accent`, `tab font`, `scene apply`) without growing
the top-level surface. The user can argparse-tab-complete the noun, then
discover the available attributes. (Autocomplete machinery is a separate
change, but the structure is already complete-friendly.)

### D2: Asymmetric `--temporary` *surface* (not default) — flag on window only

```python
# window subparser: exposes --temporary / --no-temporary, defaults to ON
# tab subparser:    does NOT expose --temporary (kitten @ set-tab-title has no such flag)
```

Effect:

| Subcommand | `--temporary` flag exposed? | Programs inside the kitty can override via OSC-2? |
|---|---|---|
| `my-kitty window title` | Yes, defaults ON | Yes by default — `vim`, `ssh`, `npm` keep their title-setting ability. Override with `--no-temporary` for sticky. |
| `my-kitty tab title` | No | Never — `kitten @ set-tab-title` has no `--temporary` flag, and OSC-2 escapes don't route to tab titles regardless. Curated tab titles always stick. |

Empirical grounding (verified 2026-05-13 against installed kitty 0.46.2):

```
$ kitten @ set-window-title --help | grep -A2 temp
  --temporary [=no]
    By default, the title will be permanently changed and programs running
    in the window will not be able to change it again. If you want to allow
    other applications to change the window title after we have changed it...

$ kitten @ set-tab-title --help | grep -A2 temp
(no output — no --temporary flag exists on set-tab-title)
```

Alternatives considered (and rejected):
- **Symmetric flag, no-op on tab.** Surfaces `--temporary` on `tab title`
  but silently does nothing. Surprises users who pass `--temporary` and
  see no effect; obscures the underlying kitten asymmetry.
- **Symmetric default-ON for both.** Doubly wrong — tabs can't even be
  made overridable at the kitten layer, and even if they could, defaulting
  to overridable defeats the scene-durability goal.
- **Symmetric default-OFF for both, no flag.** Honest but removes the
  ability to mark a window as "I want this label to survive vim/ssh", which
  is the common use case for windows in dev workflows.

Rationale: the surface asymmetry reflects the underlying kitty API
asymmetry. Pretending the two nouns are symmetric here would either lie
to users (silent no-op) or ship a flag we cannot actually honour.
`BooleanOptionalAction` on the window subparser gives the user the
override they need; the absent flag on tab is documented in `--help`
text.

### D3: Socket discovery — `$KITTY_LISTEN_ON` → `pgrep -x kitty` → error

Discovery order:

1. `$KITTY_LISTEN_ON` is set → use it unchanged. Cheap and respects the
   user's explicit context.
2. Otherwise → `pgrep -x kitty`:
   - Exactly one PID → resolve to `unix:/tmp/kitty-<PID>`, the path kitty
     auto-suffixes when `listen_on unix:/tmp/kitty` is configured (verified
     by `phase2-remote-control-foundation` probe 01).
   - Zero kitties → exit non-zero with `"no kitty process found; run kitty
     first or pass --to unix:<path>"`.
   - Two or more kitties → exit non-zero with `"multiple kitty processes
     (PIDs: X, Y); pass --to unix:/tmp/kitty-<pid> to disambiguate"`.
3. `--to unix:<path>` always wins (passed through to `kitten @ --to`).

Alternatives considered:
- **Compositor-API focused-window discovery** (X11: `xdotool` /
  `_NET_ACTIVE_WINDOW`, Wayland: protocol extension). Heavy, X11-only on
  the user's daily host, doesn't actually answer the question "which kitty
  socket" without traversing the `_NET_WM_PID` chain. Overkill for §8.
- **Always require `--to`.** Honest but punishing: the in-kitty case
  (where `$KITTY_LISTEN_ON` is set) is the ergonomic 95%-path; forcing the
  user to type the socket each time would discourage adoption.

Rationale: the chosen rule covers the in-kitty case implicitly and gives a
clear, non-magical failure mode when ambiguity is real. The
`_pgrep_kitty_pids` helper already exists in `doctor.py` and is exercised
by `tests/integration/test_h21_remote_control_foundation.py`.

### D4: `src/kitty_setup/scenes/` package, with `_client.py` as the shared `kitten @` wrapper

Layout:

```
src/kitty_setup/scenes/
    __init__.py
    _client.py    # kitten_at(verb, *args, to=None) — single socket discovery path
    title.py      # set_window_title, set_tab_title
```

`_client.py` exports:

```python
def kitten_at(
    verb: str,
    *args: str,
    to: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `kitten @ [--to <socket>] <verb> <args...>`.

    Resolves `to` via the D3 discovery order if not given.
    Raises SocketDiscoveryError on zero/multiple kitties when discovery is needed.
    """
```

Alternatives considered:
- **Flat `src/kitty_setup/title.py`** (no package). Cleaner today, ugly
  tomorrow when §9-§14 add five more modules at the top level.
- **`src/kitty_setup/scenes.py`** (single file). Forces every future
  primitive into one module; loses per-primitive test isolation.

Rationale: the package shape anticipates §9-§14 without paying for them
now. `_client.py` is the single point where the `kitten` binary path
(`installer.DEFAULT_DEST / "kitty.app" / "bin" / "kitten"`), socket
discovery, and subprocess invariants live — every future primitive imports
it and stays small.

### D5: Lift `_pgrep_kitty_pids` and `_parse_listen_on_base` out of `doctor.py`

Move both helpers from `src/kitty_setup/doctor.py` into
`src/kitty_setup/scenes/_client.py` (or a lower-level `kitten.py` if
circular import concerns surface). `doctor.py` imports them back via
`from kitty_setup.scenes._client import _pgrep_kitty_pids, _parse_listen_on_base`.

Behaviour-preserving refactor: the existing
`tests/unit/test_doctor_remote_control.py` continues to pass without
modification beyond import-path updates in its own internals (if any).

Rationale: the alternative — duplicating the helpers — diverges over time;
the helpers are already small and pure (no doctor-specific state). Keeping
one canonical implementation under `scenes/_client.py` aligns with where
the runtime callers live.

### D6: Hypothesis-first promotion under `tmp/h22-window-title/`

`tmp/h22-window-title/run.py` is an autonomous probe per
`docs/agent-iteration.md` R3: spawns a kitty, sets window + tab titles
directly via `kitten @ set-window-title` / `set-tab-title` shellouts,
verifies via `kitten @ ls`. Emits `actual.json`; compared against
`expected.json` (committed). `repro.md` captures the steps for the user to
re-run on their host.

Promotion (after autonomous green): extract the working logic into
`scenes/title.py` + `_client.py`, wire `cli.py`, port the probe assertions
into `tests/integration/test_h22_window_title.py`, delete
`tmp/h22-window-title/`.

Rationale: enforces the repo-wide hypothesis discipline. Keeps any shape
discoveries (a flag default that turns out wrong, a discovery edge case
not covered above) cheap to fix before they ossify in `src/`.

## Risks / Trade-offs

- **Tab-bar emoji rendering depends on system font fallback.** The wire
  protocol round-trips bytes faithfully (verified), but whether the user
  sees `🐳` in the tab bar depends on the active font's emoji glyph
  coverage. → Mitigation: document in `docs/repro/h22-window-title.md`
  under "Known limitations"; not in scope for §8 to ship an emoji-capable
  font.
- **`pgrep -x kitty` matches all kitty processes regardless of user.** On
  shared hosts this could surface processes the user doesn't own. →
  Mitigation: the resulting socket path `/tmp/kitty-<PID>` is UID-gated by
  the kernel (per `kitty-remote-control` spec), so a stranger's socket
  fails closed with a permission error. The user-facing error message is
  unambiguous about the discovery hit. Not blocking.
- **Asymmetric `--temporary` defaults are surprising on first read.** → Mitigation:
  document explicitly in the `kitty-scenes` spec, in `--help` text, and in
  the repro doc.
- **`scenes/` package signals "we're going to add a lot here."** It is
  intentional and bounded by Phase 2 scope (§8-§14), but a casual reader
  might think Phase 3+ also lives here. → Mitigation: brief module
  docstring in `scenes/__init__.py` referencing the Phase 2 scope in
  `docs/requirements.md`.
- **Refactor of doctor helpers could regress the
  `kitty-remote-control` check.** → Mitigation: the existing unit tests
  (`tests/unit/test_doctor_remote_control.py`, 9 tests) and integration
  test (`tests/integration/test_h21_doctor_remote_control.py`) cover the
  paths; both must pass post-refactor.
- **Integration tests are gated on `KITTI_INTEGRATION=1` and a real kitty
  binary.** → Mitigation: same gate the existing h21 tests use; CI doesn't
  exercise them; the user's host is the verification path. This is the
  project-wide pattern, not a new risk.

## Migration Plan

No migration needed — this change adds new subcommands and a new package
without modifying user-facing state. The doctor-helper refactor (D5) is
internal and behaviour-preserving.

Rollback: revert the change; the new subcommands disappear; the helpers
move back to `doctor.py`. No on-disk state is created or modified by the
title primitive at runtime — `kitten @` operates on the live kitty
process, not on config files.

## Open Questions

- Should the `--match` flag accept arbitrary kitty match expressions (e.g.,
  `id:5`, `state:focused`, `recent:0`) or expose a constrained subset? The
  full grammar is documented in `kitty @ --help` and is the same wire
  format `kitten @` accepts. **Tentative answer:** pass through unchanged,
  with a `--help` reference to the kitten match-expression docs. Surfaces
  power without us re-implementing parsing.
- Should `set_window_title` / `set_tab_title` accept an optional
  `--ignore-not-running` (or similar) flag to make the command a no-op
  when no kitty is found, suitable for unconditional invocation from
  shell-prompt hooks? **Tentative answer:** no for §8. Fail-loud matches
  the doctor-style ergonomics of the rest of the project. Revisit if §13
  named-scene invocation surfaces a use case.
