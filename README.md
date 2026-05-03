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
- No `sudo` is required. Everything lands under `~/.local/` and `~/.config/kitty/`.

## Quickstart

```bash
make setup              # install kitty into ~/.local/kitty.app, inject our config block
make doctor             # verify install state (kitty version, sentinel block, parse, paths)
make test               # unit tests (integration tests skipped without KITTI_INTEGRATION=1)
KITTI_INTEGRATION=1 make test    # run the autonomous integration tests against real kitty
make uninstall          # remove our install + strip our config block (backups kept)
make clean              # wipe ./tmp/ scratch and uninstall our config block (keeps kitty)
```

`make help` (the default target) lists every target.

## Stack and layout

Python is the stack. Bash exists only inside `tools/setup.sh` and `tools/uninstall.sh`
for prerequisite bootstrap. Everything else is a Python entry point under
`src/kitty_setup/`, exposed via `[project.scripts]` in `pyproject.toml`.

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
│   ├── installer.py       # kitty upstream install + verify + uninstall
│   ├── config_updater.py  # sentinel-bracketed include, backup, idempotent
│   ├── doctor.py          # install + config diagnostic
│   └── harness/           # autonomous test infrastructure
│       ├── kitty_session.py
│       └── cli.py
├── tools/                 # bash glue, only allowed in bootstrap territory
│   ├── setup.sh
│   └── uninstall.sh
├── config/kitty/          # promoted kitty config snippets, loaded via include
│   ├── kitty-setup.conf   # entry, includes the per-topic files below
│   ├── windowing.conf     # cwd inheritance bindings
│   └── bindings.conf      # instant clear binding
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
