# H25 — Scene launcher: one-shot tab + layout + N pre-styled panes

**Capability:** kitty-scenes (Phase 2 §12).

**Status:** Promoted. Implementation in
[`src/kitty_setup/scenes/launcher.py`](../../src/kitty_setup/scenes/launcher.py)
(Pane dataclass + hand-written pane-spec parser + 6-step kitten call algorithm)
and [`src/kitty_setup/cli.py`](../../src/kitty_setup/cli.py) (the `scene launch`
subparser). Integration tests under
[`tests/integration/test_h25_scene_launcher.py`](../../tests/integration/test_h25_scene_launcher.py).
Unit tests under
[`tests/unit/test_scenes_launcher.py`](../../tests/unit/test_scenes_launcher.py).

## Why

Phase 2 §12 of `docs/requirements.md` asks for one-shot composition: from a
daily shell, the user invokes a single command and ends up with a new tab
containing a chosen layout + N pre-styled panes, each with its own title,
optional per-pane background color, and an optional startup command. This is
the first composition primitive in Phase 2 — it consumes the §8 title, §9
accent, §10 background, and §11 mirrored Tall primitives that already ship —
and unblocks §13 (named scenes / TOML recipes) and §14 (chord-to-scene
wiring).

The wire-level questions ("how much can `kitten @ launch --type=tab` combine
in one call?", "what does it return?", "do subsequent launches race the new
tab?", "how long does a 3-pane scene take?") were settled by
`tmp/h25-scene-launcher/run.py` (green against kitty 0.46.2 on the user's
daily host) — see the probe's `repro.md` for the locked
`expected.json` findings. The headline:

- `kitten @ launch --type=tab` combines `--tab-title`, `--cwd`, `--title`,
  `--hold`, and a positional `bash -lc <cmd>` in ONE call.
- The new tab is focused synchronously; subsequent `--type=window` calls
  land in it race-free without `--match`.
- `--type=tab` returns the new tab's first WINDOW id (NOT the tab id);
  `--match recent:0` is the right tab handle for follow-up calls.
- A full 3-pane scene completes in 6 kitten calls / ~85 ms — well inside
  one human-perception frame.

The shipped change exposes this as a single `my-kitty scene launch`
subcommand with a `--pane key=value` shape that escapes commas inside values
as `\,`. The launcher is a pure Python module composing over
`scenes._client.kitten_at()` — no new socket discovery, no new dependencies.

## Manual repro

1. `make install` (or `uv tool install --force .`) to ship the updated
   `my-kitty` binary with the new `scene launch` subcommand on `$PATH`.
2. From a kitty shell, invoke the docker-monitor recipe:

   ```bash
   my-kitty scene launch \
       --layout=tall:mirrored=true \
       --tab-title="🐳 docker-mon" \
       --tab-accent=#ff851b \
       --pane 'title=ps,cmd=docker ps' \
       --pane 'title=stats,bg=#001f3f,cmd=docker stats' \
       --pane 'title=shell'
   ```

3. Observe:
   - A NEW tab appears with the title `🐳 docker-mon` and an orange tab
     accent (focused-tab background).
   - The active layout is mirrored Tall — one full-height pane on the
     right, two stacked top/bottom on the left.
   - Three panes with titles `ps`, `stats`, `shell` in order.
   - The `stats` pane has a dark navy (`#001f3f`) background.
   - The `ps` and `stats` panes are running `docker ps` and `docker stats`
     respectively; the `shell` pane is at a fresh prompt.
4. Close the tab via `ctrl+shift+q`. Re-invoke the same command — observe
   a second, independent tab is built (no idempotency; §12 is one-shot).
5. Confirm via `kitten @ ls`: the new tab's `layout_opts.mirrored` is `"y"`;
   the new tab contains exactly 3 windows with the three expected titles in
   order; `kitten @ get-colors --match id:<stats-pane-id>` reports
   `background #001f3f`.

## Linux Status

`pending verification` — to be updated to
`verified (YYYY-MM-DD, Pop!_OS 24.04 + COSMIC + kitty 0.46.2)` after the
user signs off on the manual repro above as part of §8.3 of the
`phase2-scene-launcher` apply pass.

## macOS Status

`deferred-with-reason` — no Mac host available. `kitten @ launch`,
`kitten @ set-colors`, `kitten @ set-tab-color`, and `kitten @ goto-layout`
are platform-agnostic; the only macOS-specific concerns are tab-strip
composition (the focused-tab accent rendering and tab title font rendering
under macOS's native tab-bar style) and per-pane background visual fidelity
(macOS's window-server-level compositing vs Linux/Wayland). Tracked under
follow-up `phase2-scene-launcher-macos`.

## Attempted alternatives

| Approach | Status | Why rejected |
|---|---|---|
| Shape B — repeated per-attr flags (`--pane-title X --pane-cmd Y --pane-bg Z` triples) | Rejected | Position-coupling is implicit; verbose for >2 panes; misalignment is easy to introduce by deleting one element of a triple. |
| Shape C — single JSON blob (`--scene '{"panes": [...]}'`) | Rejected | Unambiguous and scales, but shell quoting is awful for hand typing; saves a parser at the cost of UX. |
| Shape D — defer §12; only ship §13 named scenes | Rejected | Violates roadmap ordering (§12 BEFORE §13) and removes the one-shot daily-shell use case that motivates the primitive. |
| `shlex` for pane parsing | Rejected | `shlex` is shell-like quoting (single/double quotes, escape sequences inside quotes); we want literal-comma escape ONLY. Using `shlex` would make `--pane "title=docker ps"` parse differently than `--pane title='docker ps'`, the kind of surprise we want to avoid. |
| `csv` for pane parsing | Rejected | `csv.reader` does not support backslash escapes; it uses double-quoting (`"a,b"` for a comma inside a field). That clashes with shell quoting layered above. |
| `--no-response` on every `kitten @ launch` | Rejected | Loses the window id needed for deterministic per-pane styling. We always capture the id from stdout so `set-colors` targets via `--match id:<exact_id>` rather than `--match recent:0` (which drifts if anything else launches between our calls). |
| Walking `ls` from `win0` up to its tab id and using `--match tab_id:<id>` for the accent call | Rejected for §12 | Costs one extra kitten call. `--match recent:0` is probe-verified to route correctly to the just-built tab; the only race window is a ~85 ms gap during which the user would have to tab-switch — too small to be a real concern. Upgrade path documented in Known Limitations. |
| Auto-append `; exec bash` to every user-supplied `cmd` (so the user gets an interactive prompt after the command finishes) | Rejected | The user-supplied command is the contract; appending `exec bash` would be a surprising side effect. Users who want interactivity pass `cmd='docker stats ; exec bash'` explicitly. |

## Known limitations

- `--hold` is ALWAYS passed to `kitten @ launch`. Panes whose startup
  command exits immediately (`echo hi`, `docker ps | head`) stay visible
  showing the output until the user explicitly closes them. This is the
  desired default but may surprise. Users who want the pane to close on
  command exit should pass `cmd='<cmd>; exec false'` or similar.
- Partial-scene state on mid-launch failure is NOT auto-cleaned. If
  `kitten @ launch` succeeds for panes 1 and 2 but pane 3's command is
  malformed, the user sees a half-built tab; close with `ctrl+shift+q`
  and re-invoke. The launcher fails hard on launch errors (propagates the
  kitten exit code) but does NOT call any "close this tab" cleanup —
  there is no kitten verb for "close exactly this tab id" that survives
  user tab-switches.
- `--tab-accent` uses `--match recent:0` to target the just-built tab.
  There is a ~85 ms window between the tab launch and the set-tab-color
  call during which a user tab-switch could land the accent on the wrong
  tab. Documented as acceptable for §12; the upgrade path is to walk
  `ls` from the returned window id up to its tab id at the cost of one
  extra kitten call.
- No `scene close` / `scene list` surface in §12. Scenes are one-shot;
  persistence concepts (named scenes, scene catalogs) are deferred to §13.
- Per-pane opacity is NOT supported. Kitty's opacity is OS-window-scoped
  (per h23's findings); `--pane bg=…` IS supported because
  `kitten @ set-colors background=…` IS per-window.
- `--tab-accent` sets ONLY the focused-tab background (single `active=`
  key on `set-tab-color`). This is intentionally narrower than the
  `my-kitty tab accent` primitive, which sets both `active_bg=` and
  `inactive_bg=` for full persistent styling. The launcher applies the
  minimal correct behavior at launch time; if the user wants the accent
  to persist when the tab loses focus, they can chain `my-kitty tab
  accent <color>` after `my-kitty scene launch`.
- The pane-spec parser preserves any `\X` sequence verbatim if `X` is
  neither `,` nor `\`. Only `\,` and `\\` are recognised escapes. Users
  do not need to escape any character other than commas and backslashes
  inside `--pane` values.

## Recipes

### Docker monitoring

```bash
my-kitty scene launch \
    --layout=tall:mirrored=true \
    --tab-title="🐳 docker-mon" \
    --tab-accent=#ff851b \
    --pane 'title=ps,cmd=docker ps' \
    --pane 'title=stats,bg=#001f3f,cmd=docker stats' \
    --pane 'title=shell'
```

Right-handed main pane shows `docker stats` (with the navy background to
flag "monitoring"); two left-stacked panes show `docker ps` and a fresh
shell. Tab tinted orange.

### AI plan + review side-by-side

```bash
my-kitty scene launch \
    --layout=tall:mirrored=true \
    --tab-title=ai-plan \
    --pane 'title=plan,cmd=claude --plan' \
    --pane 'title=review,cmd=claude --review'
```

Two panes split right-handed. The full-height right pane runs `claude
--plan`; the left pane runs `claude --review`. Tab title `ai-plan`. Useful
during a feature design review where the planning and reviewing tools want
parallel attention.

### Compose with the h22 title primitive

```bash
my-kitty scene launch --tab-title=base --pane 'title=p1' --pane 'title=p2'
my-kitty tab title "🔍 review — diffs ready"
my-kitty tab accent "#0066cc"
```

Launches the scene, then upgrades the tab title + accent via the dedicated
primitives once it's clear what the tab will be used for. This becomes one
chord under §14 (chord-to-scene wiring).

### Pane title containing a literal comma

```bash
my-kitty scene launch \
    --pane 'title=docker ps -a\, --filter status=running,cmd=docker ps'
```

The `\,` escape preserves the literal comma in the title. The `cmd` value
contains an `=` which the parser handles by splitting each segment on the
FIRST `=` only — `cmd=docker ps` is parsed correctly.

### Override socket discovery (multi-kitty hosts)

```bash
my-kitty scene launch \
    --to=unix:/tmp/kitty-12345 \
    --pane 'title=solo,cmd=watch -n1 date'
```

When `pgrep -x kitty` returns more than one PID (e.g., two daily kitty
sessions), pass `--to` explicitly. The base socket path is the value of
`listen_on` in `~/.config/kitty/kitty-setup/remote-control.conf`; append
`-<pid>` to target a specific instance.
