## Context

The bootstrap change shipped three `[project.scripts]` entries reachable only
via `uv run` from inside the repo directory. The user-experience problem this
creates was articulated in two ways during planning:

1. *"After `make install` I should be able to delete the repo and the tool
   should keep working."* — the `uv run` model couples the binary's
   existence to the source directory. Delete the repo and the binary is gone.
2. *"Inside any kitty window I want to type one command and see what
   bindings I have."* — three CLI names with `kitty-setup-` prefixes are
   unwieldy and not on PATH globally without manual setup.

The fix is structural: collapse to one binary with subcommands (the wez-tab
model the user pointed at as a reference shape), install it through a
mechanism that decouples it from the source repo, and ensure it lands on PATH.

The probe pass for this change settled the install mechanism. `uv tool
install .` (frozen, NOT `--editable`) builds a private tool venv at
`~/.local/share/uv/tools/<pkg>/` with the source COPIED in (probe 02), drops
real entry-point shims at `~/.local/bin/<entry>` (probe 01), survives
deletion or relocation of the source repo (probe 03), and removes cleanly via
`uv tool uninstall <pkg>` (probe 04). Re-install latency: 177 ms — well
below any "needs a fast path to skip" threshold.

## Goals / Non-Goals

**Goals:**

- One binary on PATH after `make install`: `my-kitty-setup`. Subcommands:
  `install`, `uninstall`, `doctor`, `help`. Argparse subparsers; one help
  tree.
- The binary lives at `~/.local/bin/my-kitty-setup` (uv-managed shim) and
  works regardless of whether the source repo still exists.
- `make install` is the single user-facing command for both first install
  and updates. Internally it ensures uv → `uv sync` → `uv tool install
  --force .` → ensure `~/.local/bin` in PATH → `my-kitty-setup install`.
- `make uninstall` strips our config + payload. Optional flags wipe kitty
  (`--kitty`) and print the manual command for self-removal (`--self`).
- Source repo can be deleted any time after `make install` completes; the
  binary keeps working and updates re-pull the repo (`git clone` or
  `git pull`) before re-running `make install`.
- Per-change probe subdirectory convention: `tmp/probes/<change-id>/`
  documented in `docs/agent-iteration.md`, modifying the existing
  `agent-iteration-discipline` spec to match.

**Non-Goals:**

- macOS-specific install paths (`~/Applications/kitty.app`). Defer to
  `add-macos-install-path`.
- Kitty `--upgrade` semantics (fetch + reinstall when remote upstream is
  newer than the local). Defer to `add-kitty-upgrade-flag`.
- Bash + zsh tab-completion sourcing. Defer to `add-shell-completion`.
- The `keys` subcommand and OS-shadow detection. The parked
  `phase1-binding-introspection` change picks them up after this archives.
- A centralised TOML config file. Defer until a second user surfaces
  with personalisation needs.
- Self-removal that the binary itself executes (`my-kitty-setup uninstall
  --self` runs the `uv tool uninstall`). Print the manual command instead;
  process-killing-its-own-binary is a sharp edge with no current need.

## Decisions

### D1 — Install mechanism: `uv tool install --force .` (non-editable)

The probes settled this. Non-editable so the source is COPIED into the tool
venv (probe 02), satisfying the "delete the repo after install" requirement
(probe 03). `--force` so re-runs idempotently replace the tool venv with the
current source (every `make install` re-runs the same command; no "skip if
installed" branch needed because the operation is 177 ms).

**Alternative considered:** symlink `.venv/bin/my-kitty-setup` →
`~/.local/bin/my-kitty-setup`. Rejected — symlink target lives inside the
source repo's `.venv/`, breaks if `.venv/` is wiped or the repo moves. The
symlink option only works while the repo stays in place, which directly
contradicts the user requirement.

**Alternative considered:** `pipx install .`. Rejected — works but adds a
new system dependency (pipx) that we don't already have. uv is already in
the stack and gives us identical semantics via `uv tool install`.

**Alternative considered:** `uv tool install --editable .`. Rejected for the
deployable. We DO use `uv sync` (which installs editable into `.venv/`) for
dev work — that's how the test suite continues to test the live source.
But the deployable on PATH must be the frozen, copied install.

### D2 — Uninstall has three layered scopes

The user can want different things removed:

1. **Always** — our kitty config block + payload directory under
   `~/.config/kitty/kitty-setup/`. This is what `my-kitty-setup uninstall`
   does with no flags. Equivalent to today's `kitty-setup-install
   --uninstall-config`.
2. **`--kitty`** — also removes `~/.local/kitty.app/`, the
   `~/.local/bin/kitty` symlink, and the desktop entry. Equivalent to
   today's `tools/uninstall.sh`.
3. **`--self`** — prints (does NOT execute) the manual command
   `uv tool uninstall my-kitty-setup` and a one-line description of the
   shell-rc PATH cleanup. The user types the command themselves.

The `--self` PRINT-only behavior is intentional. Killing the running
binary's own files is reliable on Linux but has surprising failure modes
across distros and filesystems. The cost of asking the user to type one
extra line is low; the cost of getting self-uninstall wrong is a confused
user with a broken PATH. Defer the auto-self-uninstall until someone
actually needs it.

`make uninstall` calls `my-kitty-setup uninstall` with no flags by default.
`make uninstall ALL=1` adds `--kitty --self`.

### D3 — PATH integration via sentinel-bracketed shell-rc edit

Mirror the kitty.conf injection pattern. Detect the user's shell from
`$SHELL`, pick `~/.zshrc` or `~/.bashrc` as the target. Append between
markers if missing:

```
# >>> my-kitty-setup PATH >>>
export PATH="$HOME/.local/bin:$PATH"
# <<< my-kitty-setup PATH <<<
```

Idempotent: re-runs detect the block and skip. If `~/.local/bin` is already
in `$PATH` (parsed from the file's `export PATH=...` lines AND from the
current process env to handle pre-set PATHs), skip the write entirely.
Sentinel bracketing makes future cleanup mechanical.

**Alternative considered:** modify `/etc/profile` or system-wide config.
Rejected — requires root, violates the per-user no-sudo principle.

**Alternative considered:** print "please add `~/.local/bin` to PATH"
instead of editing. Rejected — silently breaks for users who don't read
the install output. The wez-tab reference does the auto-edit and our
sentinel pattern makes it reversible.

### D4 — Subcommand dispatch via argparse subparsers, not Click

Argparse is in stdlib; Click is a runtime dependency. The subcommand tree
is small (4 today, ~8 next year) and argparse's subparser API handles it
fine. Skipping Click also keeps the wheel tiny (relevant for `uv tool
install` cold-cache install latency, even though it's already sub-second).

**Alternative considered:** Click. Rejected — extra runtime dep for no
incremental capability. Re-evaluate if the subcommand tree grows past 12
or if we need rich shell-completion ergonomics that argparse can't reach.

### D5 — Drop the `kitty-setup-harness` entry; harness is a Python module only

The harness CLI was a smoke test that booted a session and printed `ls()`.
Tests import `KittySession` directly; no other consumer exists. Removing
the CLI entry shrinks the public surface and removes a useless command from
help output. The Python class stays unchanged at
`src/kitty_setup/harness/kitty_session.py`.

### D6 — Per-change probe subdirectory

`agent-iteration-discipline` currently says probes live at
`tmp/probes/<NN>-<slug>.md`. With concurrent in-flight changes that
collides on `01-*.md`, `02-*.md`, etc. This change uses
`tmp/probes/consolidate-into-my-kitty-setup-cli/01-...md` and proposes the
spec delta to make that the documented convention.

**Alternative considered:** continue the flat numbering across changes
(`05-...md` for this change since the introspection change already used
01-04). Rejected — couples ordinals across changes, breaks the
"per-change ordinal restarting from 01" rule the discipline spec is built
on.

## Risks / Trade-offs

* **Risk: uv tool install requires uv ≥ 0.5 or so.** Earlier uv versions
  may not support `tool install`. → *Mitigation:* `tools/setup.sh` already
  installs the latest upstream uv if missing. We pin a minimum uv version
  in the install logic and fail fast with a clear message if older uv is
  detected. Probe re-runs are cheap if uv changes.
* **Risk: `~/.local/bin` is not on the user's PATH and our rc edit doesn't
  fire (e.g. user uses fish, or a non-standard rc location).** → *Mitigation:*
  D3 covers `~/.zshrc` and `~/.bashrc`; we print a clear message if the
  detected shell is unsupported (fish, nushell, etc.) and tell the user
  the one line to add manually. Add fish support in a follow-up if anyone asks.
* **Risk: argparse subparser help is uglier than Click's.** → *Mitigation:*
  customise the help formatter with a short banner; subcommands are listed
  with one-line descriptions. Acceptable for a 4-subcommand tree.
* **Risk: existing OpenSpec specs (kitty-install, kitty-config-management)
  reference `make setup` / `kitty-setup-install` etc. This change replaces
  those mechanisms.** → *Mitigation:* the existing specs are written
  implementation-agnostic ("the system shall install …", "doctor reports
  …"), not coupled to specific entry-point names. They keep applying. The
  new `my-kitty-setup-cli` capability owns the new mechanism; no MOD
  needed on `kitty-install` or `kitty-config-management`.

## Migration Plan

This is the first non-behavior-additive change in the repo. No data
migration. The migration is mechanical: existing users (just me, today) run
`make uninstall` (which drops config under the OLD `uv run kitty-setup-install
--uninstall-config` path), then `git pull`, then `make install` (the new
flow). Or skip uninstall entirely and `make install` since the new flow is
idempotent — the only stray artefact would be the old entries from the
previous `uv tool install` we did during probes, which the new install
overwrites.

Deploy:

1. `git pull` (or `git clone <repo>`).
2. `make install` → ensures uv → `uv sync` → `uv tool install --force .` →
   ensures `~/.local/bin` in PATH → `my-kitty-setup install` → kitty
   downloaded if missing, config block + payload re-applied idempotently.
3. New shell sessions pick up the rc PATH edit; current session can
   `source ~/.zshrc` (or `~/.bashrc`) or restart.

Rollback:

1. `make uninstall ALL=1` → strips config block, removes payload, removes
   kitty install + symlink + desktop entry, prints the
   `uv tool uninstall my-kitty-setup` and the rc-edit cleanup commands.
2. User runs the printed commands to fully wipe the binary and PATH edit.
3. Repo can be deleted afterwards. Backups under
   `~/.config/kitty/kitty.conf.bak.*` are preserved.

## Open Questions

* **Q1 — Should the `--self` flag eventually run the uninstall instead of
  printing it?** Today: print only. Re-evaluate after observing whether
  users actually copy-paste the printed line or get confused. Likely
  resolution: keep print-only until a second user complains.
* **Q2 — `~/.zshrc` vs `~/.zshenv` vs `~/.zprofile` for the PATH edit?**
  `.zshrc` runs for interactive shells; `.zshenv` runs for ALL shells
  including non-interactive (which matters for `cron`, scripts). For now
  `.zshrc` is enough — `make install`-installed tools are interactive-use
  by design. Revisit if non-interactive use surfaces.
* **Q3 — Should we detect fish (a popular alternative shell) and warn?**
  Today: yes, warn with the manual line to add. Auto-edit fish config in
  a follow-up if someone asks.
* **Q4 — The `phase1-binding-introspection` change is parked at commit
  `ad6dd2d`. Does it need rewriting before re-applying, or only minor
  retargeting (rename `kitty-setup-bindings` → `my-kitty-setup keys`)?**
  Likely the latter — the introspection module's logic is independent of
  whether it's exposed as its own entry or as a subcommand. Spec text in
  the parked change references the old name and `[project.scripts]` entry;
  amend before resuming.
