# Scene recipes — named, declarative TOML scenes

**Capability:** kitty-scenes (Phase 2 §12, declarative half / roadmap bullet 7).

**Status:** Promoted. Loader in
[`src/kitty_setup/scenes/recipe.py`](../../src/kitty_setup/scenes/recipe.py)
(`scenes_dir`, `load_scene`, `list_scenes`, `cli_scene_list`); name-mode dispatch
in [`src/kitty_setup/scenes/launcher.py`](../../src/kitty_setup/scenes/launcher.py)
(`cli_scene_launch`); CLI wiring (positional `name` on `scene launch`, sibling
`scene list`) in [`src/kitty_setup/cli.py`](../../src/kitty_setup/cli.py).
Unit tests under
[`tests/unit/test_scenes_recipe.py`](../../tests/unit/test_scenes_recipe.py);
end-to-end integration test under
[`tests/integration/test_scene_recipe_e2e.py`](../../tests/integration/test_scene_recipe_e2e.py).

## Why

The imperative half (`my-kitty scene launch --pane …`, h25) ships a complete
launch engine — `launch_scene(layout, tab_title, tab_accent, list[Pane])` — but
its authoring surface is a comma-separated, backslash-escaped flag string. Phase
2 §12 / roadmap bullet 7 asks for the *recipe* form: define a scene once in a
file, launch it by name. TOML is the natural authoring surface the inline form
can't be — native strings mean no `\,` / `\\` escaping for commands like
`docker run --env VAR=value bash`.

This change is a pure **front-end**: read a named TOML file, build the four
arguments `launch_scene()` already takes, and call it unchanged. No new
kitten-call behavior is introduced — the wire algorithm is settled by the h25
probe — so **no new `tmp/hNN` probe** is warranted. The new surface (TOML→args)
is deterministic and covered by unit tests plus one end-to-end integration test.

The recipe loader imports `Pane` from `launcher.py` and derives its recognised
`[[pane]]` keys from `Pane`'s fields, so the declarative and inline forms can
never silently diverge (the `active=` / `active_bg=` drift lesson from the
launcher).

§13 (named *presets* referenced by name — window/tab presets composed into
scenes) is a separate, richer capability. This change ships **flat** recipes
only: `[[pane]]` holds inline definitions, not preset references.

## Manual repro

1. `make install` (or `uv tool install --force .`) to ship the updated
   `my-kitty` binary with the positional `scene launch <name>` and the new
   `scene list` subcommand on `$PATH`.
2. Author a recipe (scene name = file stem). The repo ships ready-to-copy
   samples under `examples/scenes/`:

   ```bash
   mkdir -p ~/.config/kitty-setup/scenes
   cp examples/scenes/docker.toml examples/scenes/edit.toml \
      ~/.config/kitty-setup/scenes/
   # docker.toml = 3-pane dashboard; edit.toml = single pane
   ```

3. List what's available — a column-aligned table:

   ```bash
   my-kitty scene list
   # NAME    TAB        PANES
   # docker  🐳 docker  3
   # edit    -          1
   ```

   Tab-completion works on the name: `my-kitty scene launch <TAB>` offers
   `docker`, `edit`, … (requires the argcomplete eval line `make install` sets up).

4. Launch the multi-pane scene from a kitty shell:

   ```bash
   cd ~/some/project
   my-kitty scene launch docker
   ```

5. Observe: a NEW tab titled `🐳 docker` with an orange focused-tab accent;
   mirrored Tall layout; three panes `ps`, `stats`, `shell` in order; the `stats`
   pane on a dark-navy (`#001f3f`) background. Because no pane set `cwd`, every
   pane opens in `~/some/project` (the directory you launched from).
6. Launch the **single-pane** scene and watch where it lands:

   ```bash
   my-kitty scene launch edit
   ```

   It does NOT open a new tab — the one window joins your CURRENT tab (a new
   split), inheriting the launch directory. `tab_title`/`tab_accent`/`layout`
   are ignored for a one-pane scene.
7. Confirm via `kitten @ ls`: the multi-pane scene's new tab has
   `layout_opts.mirrored == "y"`, three ordered windows, the `stats` background
   `#001f3f`, and each window's `cwd` is your launch directory.
8. Error / guard surfaces to try:
   - `my-kitty scene launch nope` → exits non-zero, lists available scenes.
   - `my-kitty scene launch docker --pane 'title=x'` → exits non-zero
     ("contradictory").
   - `my-kitty scene launch docker --tab-accent=#fff` → exits non-zero
     (the recipe file is authoritative).
   - `my-kitty scene launch ../../etc/something` → exits non-zero (invalid name;
     reads nothing outside the scenes directory).

## Linux Status

`verified (2026-06-05, Pop!_OS 24.04 + COSMIC + kitty 0.47.1)` — the e2e
integration test `tests/integration/test_scene_recipe_e2e.py` passes against a
live kitty (`KITTI_INTEGRATION=1`): a temp `demo.toml` launched by name produces
a new `recipe-e2e` tab, mirrored Tall layout, three ordered panes `p1`/`p2`/`p3`,
and the `p2` `#001f3f` background — the same observables the h25 inline e2e test
asserts. The 47-case unit suite (`tests/unit/test_scenes_recipe.py`) covers the
loader, schema validation, the path-traversal guard, and `scene list` output
host-independently.

## macOS Status

`deferred-with-reason` — no Mac host available. The declarative layer is pure
local file IO + TOML parsing (platform-agnostic) and reuses the unchanged
`launch_scene` engine, whose `kitten @` calls are themselves platform-agnostic.
The only macOS-specific concerns are inherited from the launcher (tab-strip
accent rendering, per-pane background compositing) and tracked under the existing
`phase2-scene-launcher-macos` follow-up.

## Attempted alternatives

| Approach | Status | Why rejected |
|---|---|---|
| One multi-scene file (`scenes.toml` with `[scenes.<name>]` tables) | Rejected | Nested pane arrays get verbose (`[[scenes.<name>.pane]]`); `scene list` must parse the whole file; one-file-per-scene makes `list` a directory read and keeps `[[pane]]` flat. |
| New verb `scene up <name>` / `scene load <name>` | Rejected | Overloading `scene launch` with an optional positional keeps the inline and named forms one gesture; a separate verb fragments the surface. |
| `scene launch list` for enumeration | Rejected | Collides with the positional — it would parse as "launch a scene named `list`". `scene list` is a sibling sub-subcommand. |
| Allow style-flag overrides in name mode (`scene launch mon --tab-accent=…`) | Deferred | Genuinely useful one-off tints, but widens scope; the recipe file is authoritative for v1. |
| Redefine a `Pane`-like schema struct in `recipe.py` | Rejected | Importing `Pane` from `launcher.py` and deriving recognised keys from its fields prevents silent schema drift between the inline and declarative forms. |
| `cmd` as an argv array | Deferred | The engine wraps `cmd` as `bash -lc <str>`; string-only keeps the engine untouched. An array form is a future nicety. |
| Ship an example scene as managed payload | Rejected | It would be clobbered on reinstall and sits in user-data space; the empty-state hint and this repro doc carry the example instead. |

## Known limitations

- **Flat recipes only.** `[[pane]]` holds inline definitions. Named window/tab
  presets referenced by name (§13) are a separate change.
- **Single-pane → current tab.** A one-pane scene opens a window in your current
  tab and ignores `tab_title`/`tab_accent`/`layout` (there is no new tab to
  style). It never commandeers the shell you launched from — it adds a split.
- **Multi-pane → current tab when launched inside kitty.** A scene with two or
  more panes launched from a shell inside kitty (`$KITTY_WINDOW_ID` set) fills
  your CURRENT tab: the window you launched from becomes pane 0 (restyled in
  place), the rest open as splits, and `layout`/`tab_title`/`tab_accent` apply
  to that tab. No new tab is created. When launched with `$KITTY_WINDOW_ID`
  unset (driven over `--to` from another terminal, or from the test harness) a
  multi-pane scene opens a NEW tab instead, since there is no origin window to
  adopt. A pane-0 `cwd`/`cmd` on the reused window is best-effort (fed via
  `send-text` to the running shell), so prefer a plain (cmd-less) first pane.
- **cwd inheritance is "launch dir", not "active window".** Panes without an
  explicit `cwd` inherit the directory the `my-kitty` process ran in. With
  `--to=<other-kitty>` that is still the caller's dir, not the remote window's.
- **No teardown.** `scene close` / `scene down` is out of scope — a launched
  scene leaves no persistent identity to match on reliably. Deferred with reason.
- **Recipe file is authoritative in name mode.** Inline `--pane` and the style
  flags (`--layout` / `--tab-title` / `--tab-accent`) are rejected alongside a
  name; there is no per-invocation override yet.
- **One-shot, like the inline form.** Re-launching a named scene builds a second
  independent tab; there is no idempotency / convergence.
- Inherits every launcher limitation (always-`--hold`, focused-tab-only accent,
  no rollback on a mid-build styling error) — see
  [`h25-scene-launcher.md`](h25-scene-launcher.md).

## Recipes

### Docker monitoring

```toml
# ~/.config/kitty-setup/scenes/docker.toml
layout     = "tall:mirrored=true"
tab_title  = "🐳 docker"
tab_accent = "#ff851b"

[[pane]]
title = "ps"
cmd   = "docker ps"

[[pane]]
title = "stats"
bg    = "#001f3f"
cmd   = "docker stats"

[[pane]]
title = "shell"
```

```bash
my-kitty scene launch docker
```

### Single pane → current tab (no new tab)

```toml
# ~/.config/kitty-setup/scenes/edit.toml — one pane joins your current tab
[[pane]]
title = "edit"
cmd   = "${EDITOR:-vim} . ; exec bash"
```

```bash
my-kitty scene launch edit   # splits the tab you're in; inherits your cwd
```

### AI plan + review side-by-side

```toml
# ~/.config/kitty-setup/scenes/ai-review.toml
layout    = "tall"
tab_title = "🤖 review"

[[pane]]
title = "plan"
cwd   = "/home/user-zero/git/cco/kitty-setup"
cmd   = "claude"

[[pane]]
title = "diff"
cmd   = "git diff --stat ; exec bash"
```

### Command with a literal comma (no escaping needed in TOML)

```toml
[[pane]]
title = "filtered"
cmd   = "docker ps -a --filter status=running,status=exited"
```

In the inline form this needs `\,`; in TOML the string is literal.

### List and script over scenes

```bash
my-kitty scene list            # rich: name + tab title + pane count
my-kitty scene list --names    # bare names, one per line (scripting)
for s in $(my-kitty scene list --names); do echo "have scene: $s"; done
```
