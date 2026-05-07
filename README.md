# kitty-setup

Hypothesis-driven toolkit for the [Kitty terminal](https://sw.kovidgoyal.net/kitty/),
delivered in two independent components that share a repo:

- **Foundation** — Kitty config plus small scripts that fix daily friction (cwd-preserving
  tabs and windows, instant clear-screen, paste fidelity, suspend/resume stability, a
  curated cross-platform keybinding set, binding introspection, an install diagnostic).
- **Scenes** — declarative recipes that summon a themed working mode by name: a tab with
  a chosen layout, multiple pre-styled windows, and per-window startup commands. Examples:
  `docker-monitor`, `ai-plan-review`, `ai-code-review`.

> **Status**: Phase 0 → Phase 1 in flight. The first OpenSpec change
> ([`bootstrap-foundation-phase1-popos`](openspec/changes/bootstrap-foundation-phase1-popos/))
> bootstraps the install path, the autonomous test harness, and the first two Foundation
> behaviors (cwd inheritance, instant clear) on Pop!_OS 24.04. macOS parity is deferred
> until the Pop!_OS path is stable. Linux + macOS parity remains the long-term target;
> every shipped behavior will eventually be verified on both.

## Prerequisites

- Pop!_OS 24.04 (Wayland, COSMIC compositor). Other Ubuntu 24.04 derivatives likely work
  but are not validated.
- `bash`, `curl`, `make`. Pre-installed on a stock Pop!_OS box.
- A working internet connection. `make setup` downloads the upstream kitty installer and,
  if necessary, installs `uv` from `https://astral.sh/uv/install.sh`.
- `~/.local/bin` should be on `$PATH`. `make install` will append a
  sentinel-bracketed `export` to `~/.zshrc` or `~/.bashrc` if not.
- No `sudo` is required. Everything lands under `~/.local/` and `~/.config/kitty/`.

## Quickstart

```bash
make install            # uv sync → uv tool install . → kitty + config + PATH (calls tools/setup.sh)
my-kitty doctor         # verify install state (kitty version, sentinel block, parse, paths, bindings, completion)
my-kitty install        # idempotent re-run; same as `make install` after the first install
my-kitty keys           # list every active binding grouped by source; flags conflicts
my-kitty keys --json    # same data as machine-readable JSON
my-kitty <TAB>          # bash + zsh tab completion (after one make install + new shell)
make test               # unit tests (integration tests skipped without KITTI_INTEGRATION=1)
KITTI_INTEGRATION=1 make test    # run the autonomous integration tests against real kitty
make uninstall                   # remove EVERYTHING we created (config + payload + kitty + backups)
make uninstall KEEP_BACKUPS=1    # preserve kitty.conf.bak.* files; remove the rest
make uninstall KEEP_CONFIG=1     # preserve entire ~/.config/kitty/ footprint; still removes kitty.app
make uninstall KEEP_KITTY=1      # preserve kitty.app + symlink + desktop; remove config + backups
make clean              # strip our config block + wipe ./tmp/ scratch (keeps kitty + binary)
make prune              # keep 3 most recent kitty.conf backups, delete the rest
my-kitty prune          # dry-run: list backups + total size, no deletions
my-kitty prune --backups --older-than 60   # non-default policy: trim by age (days)
my-kitty prune --backups --all             # most aggressive: delete every backup
```

`make help` (the default target) lists every target.

### Chord catalog

Curated bindings ship under `kitty_mod ctrl+shift` — pinned in `kitty-setup.conf` so
the literal chord is identical on Linux and macOS (`ctrl+shift+<key>`, never `cmd+<key>`).
One `.conf` per category; `my-kitty keys` groups bindings by category.

| Category    | Chord              | Action                                                          | Source file        |
| ----------- | ------------------ | --------------------------------------------------------------- | ------------------ |
| windowing   | `ctrl+shift+t`     | new tab, inherits cwd                                           | `windowing.conf`   |
| windowing   | `ctrl+shift+n`     | new OS window, inherits cwd                                     | `windowing.conf`   |
| windowing   | `ctrl+shift+enter` | new window in tab, inherits cwd                                 | `windowing.conf`   |
| windowing   | `ctrl+shift+\`     | vsplit, inherits cwd                                            | `windowing.conf`   |
| windowing   | `ctrl+shift+/`     | hsplit, inherits cwd                                            | `windowing.conf`   |
| clear       | `ctrl+shift+x`     | clear screen + scrollback (instant)                             | `clear.conf`       |
| tab-nav     | `ctrl+shift+]`     | `next_tab`                                                      | `tab-nav.conf`     |
| tab-nav     | `ctrl+shift+[`     | `previous_tab`                                                  | `tab-nav.conf`     |
| tab-nav     | `ctrl+shift+.`     | `move_tab_forward`                                              | `tab-nav.conf`     |
| tab-nav     | `ctrl+shift+,`     | `move_tab_backward`                                             | `tab-nav.conf`     |
| tab-nav     | `ctrl+shift+q`     | `close_tab`                                                     | `tab-nav.conf`     |
| window-nav  | `ctrl+shift+h`     | `neighboring_window left`                                       | `window-nav.conf`  |
| window-nav  | `ctrl+shift+j`     | `neighboring_window down`                                       | `window-nav.conf`  |
| window-nav  | `ctrl+shift+k`     | `neighboring_window up`                                         | `window-nav.conf`  |
| window-nav  | `ctrl+shift+l`     | `neighboring_window right`                                      | `window-nav.conf`  |
| window-nav  | `ctrl+shift+w`     | `close_window`                                                  | `window-nav.conf`  |
| window-nav  | `ctrl+shift+f`     | `next_window` (round-robin focus)                               | `window-nav.conf`  |
| font-zoom   | `ctrl+shift+=`     | `change_font_size all +2.0`                                     | `font-zoom.conf`   |
| font-zoom   | `ctrl+shift+-`     | `change_font_size all -2.0`                                     | `font-zoom.conf`   |
| font-zoom   | `ctrl+shift+0`     | `change_font_size all 0` (reset)                                | `font-zoom.conf`   |
| detach      | `ctrl+shift+d`     | `detach_window ask` (interactive picker)                        | `detach.conf`      |
| detach      | `ctrl+shift+alt+d` | `detach_tab ask` (interactive picker)                           | `detach.conf`      |
| broadcast   | `ctrl+shift+i`     | `launch --allow-remote-control kitty +kitten broadcast`         | `broadcast.conf`   |
| url-hints   | `ctrl+shift+e`     | `open_url_with_hints`                                           | `url-hints.conf`   |

Notes:

- The broadcast kitten mirrors typed input to ALL kitty windows by default (not just
  the active tab). The §5 spec preamble suggests "active tab" but the action string is
  intentionally unconstrained at the spec layer; tightening the scope to the focused
  tab is tracked as a follow-up (`phase1-curated-bindings-broadcast-tab-scope`).
- macOS-only `cmd+*` parity overrides (e.g. `cmd+k` for clear) are deferred to a
  follow-up change (`phase1-curated-bindings-macos-overrides`); the curated chords
  above work as-is on macOS today.
- `my-kitty keys` reports each category as its own section. Run
  `my-kitty keys --json | jq '.summary'` to see the `0 conflicts` invariant doctored
  by `make doctor`'s `bindings` check.

The deployable binary lives at `~/.local/bin/my-kitty` (a uv-managed shim)
and the source it dispatches to is COPIED into
`~/.local/share/uv/tools/kitty-setup/` at install time. **The source repo
can be deleted any time after `make install` completes** — the binary keeps
working
(probe-consolidate-into-my-kitty-setup-cli-03).

## Backup hygiene

Every `make install` that detects drift on `~/.config/kitty/kitty.conf`
writes a timestamped `kitty.conf.bak.<UTC-ts>` next to it. Install **never**
deletes those files. Uninstall **deletes them by default** (per
simplify-uninstall-defaults — "uninstall = remove everything we put on your
system"); pass `KEEP_BACKUPS=1` to preserve them. For routine maintenance
without uninstalling, use `prune`:

```
my-kitty prune                              # dry-run listing, no writes
my-kitty prune --backups                    # default: --keep 3
my-kitty prune --backups --keep N           # keep N most recent
my-kitty prune --backups --older-than DAYS  # trim by mtime age
my-kitty prune --backups --all              # nuke everything
make prune                                  # alias of `--backups --keep 3`
```

⚠️ Pruning `--all` immediately before an install reduces rollback safety to
the same-process backup written at the start of the next install. Run prune
*after* a successful install, not before.

## Updates

```bash
git pull && make install
```

`make install` calls `uv tool install --force .`, which idempotently rebuilds
the tool venv from the current source in ~177 ms
(probe-consolidate-into-my-kitty-setup-cli-01). No "skip if installed" branch:
re-running is the supported update path.

If you upgraded from the `my-kitty-setup` era, the install prints a one-line
notice with the literal `uv tool uninstall my-kitty-setup` command — run it
to clean up the legacy shim. Your shell rc PATH block migrates automatically
from the legacy `# >>> my-kitty-setup PATH >>>` markers to the new
`# >>> my-kitty PATH >>>` markers on the same `make install` run.

**Breaking change as of `simplify-uninstall-defaults`:** `make uninstall` now
removes the entire footprint by default (config block + payload + kitty.app +
symlink + desktop entry + every `kitty.conf.bak.*` file). The pre-rename
`--kitty` and `--self` flags are gone, replaced by opt-out `--keep-backups` /
`--keep-config` / `--keep-kitty` (Make-side: `KEEP_BACKUPS=1` etc.). The
closest mapping to the legacy "config-only" default is
`make uninstall KEEP_KITTY=1 KEEP_BACKUPS=1`.

**Note as of `add-shell-completion`:** the sentinel-bracketed PATH block in
your shell rc now contains a guarded `register-python-argcomplete` eval line
in addition to the PATH export. Re-running `make install` rewrites the block
body in place between the existing markers; nothing else in the rc file is
touched. Open a fresh shell after the install — `my-kitty <TAB>` expands to
the subcommand list; `my-kitty uninstall --keep<TAB>` expands to the three
`--keep-*` flags.

## Stack and layout

Python is the stack. Bash exists only inside `tools/setup.sh` and `tools/uninstall.sh`
for prerequisite bootstrap. Everything else is a Python entry point under
`src/kitty_setup/`. Exactly one entry is exposed via `[project.scripts]`:
`my-kitty`, dispatching subcommands (`install`, `uninstall`, `doctor`,
`prune`, `help`) via argparse subparsers in `src/kitty_setup/cli.py`.

```
.
├── Makefile               # thin glue, ≤5 lines per target
├── pyproject.toml         # uv-managed Python project, [project.scripts] entry points
├── README.md
├── CLAUDE.md
├── docs/
│   ├── requirements.md            # v1 scope, source of truth for what ships
│   ├── propossal_roadmap.md       # strategic decisions for the restart
│   ├── agent-iteration.md         # hypothesis workflow playbook
│   └── repro/                     # promoted manual repros (one per behavior)
├── src/kitty_setup/       # Python package (PyPA src layout)
│   ├── cli.py             # my-kitty subcommand dispatcher (single entry point)
│   ├── installer.py       # kitty upstream install + verify + uninstall + cli handlers
│   ├── config_updater.py  # sentinel-bracketed include, backup, idempotent
│   ├── doctor.py          # install + config diagnostic
│   ├── path_integration.py# sentinel-bracketed PATH editor for ~/.zshrc / ~/.bashrc
│   └── harness/           # autonomous test infrastructure (Python module, no CLI)
│       └── kitty_session.py
├── tools/                 # bash glue, only allowed in bootstrap territory
│   ├── setup.sh
│   └── uninstall.sh
├── config/kitty/          # promoted kitty config snippets, loaded via include
│   ├── kitty-setup.conf   # entry; pins kitty_mod ctrl+shift, includes the per-topic files below
│   ├── intentional-overrides.conf  # allow-list for chords that shadow kitty defaults
│   ├── windowing.conf     # cwd inheritance bindings (5 chords)
│   ├── clear.conf         # instant clear binding (ctrl+shift+x)
│   ├── tab-nav.conf       # tab navigation (5 chords)
│   ├── window-nav.conf    # vim-style window navigation h/j/k/l (6 chords)
│   ├── font-zoom.conf     # font zoom +/-/reset (3 chords)
│   ├── detach.conf        # detach window/tab (2 chords)
│   ├── broadcast.conf     # broadcast kitten (1 chord)
│   └── url-hints.conf     # open_url_with_hints (1 chord)
├── tests/
│   ├── unit/              # fast, isolated, kitty mocked
│   └── integration/       # real kitty session, gated by KITTI_INTEGRATION=1
├── openspec/              # active and archived change proposals
└── tmp/                   # gitignored scratch for hypothesis runs (h<NN>-<slug>/)
```

## How work happens here

We do not build something and then prove it. We prove the smallest verifiable behavior
against a real kitty, then promote it. Every behavior begins as a directory under
`tmp/h<NN>-<slug>/` containing `repro.md` (manual repro and expected outcome) and
`run.py` (autonomous probe driving kitty over its remote-control socket). Only after a
green autonomous run does the behavior promote to `config/kitty/`, `src/kitty_setup/`,
`docs/repro/`, and `tests/integration/`. The agent that writes a hypothesis is not the
agent that promotes it. See [docs/agent-iteration.md](docs/agent-iteration.md) for the
full playbook.

## What this repo does NOT do (yet)

- macOS support. Deferred until the Pop!_OS path is stable.
- Phase 1 items 3–7 (binding introspection, paste fidelity, curated keybindings,
  suspend/resume stability, image-paste parity). Each lands as its own OpenSpec change.
- The Scenes layer. Phase 2.
- Kitten packaging. Phase 3, only if earned per the roadmap promotion criteria.
- Vendoring kitty, uv, or any runtime dependency. We download upstream at install time.

## License

[MIT](LICENSE).
