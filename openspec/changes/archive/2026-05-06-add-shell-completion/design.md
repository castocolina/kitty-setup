## Context

`my-kitty` ships zero shell completion today. The argparse parser at
`src/kitty_setup/cli.py:30` defines six subcommands (`install`,
`uninstall`, `doctor`, `prune`, `keys`, `help`) plus per-subcommand
flags (`--keep-backups`, `--keep-config`, `--keep-kitty`, `--no-config`,
`--dest`, `--backups`, `--keep`, `--older-than`, `--all`, `--json`,
`--config-path`). User typed `my-kitty <TAB>`, got nothing, surfaced the
gap verbally.

`argcomplete` is the canonical answer for argparse-based CLIs: a single
`autocomplete(parser)` call right before `parse_args` registers the hook.
At completion time the shell exports `_ARGCOMPLETE=1`, argcomplete
intercepts, walks the parser tree, prints candidates, exits. Normal
interactive `my-kitty <subcmd>` runs hit the no-op branch (one env-var
check + return). The shell side needs `register-python-argcomplete
my-kitty` to be eval'd into the rc once.

Constraints:
- `[project.scripts]` entry uses a uv-managed shim. The Python entry
  resolves to `kitty_setup.cli:main`; the shim is what
  `register-python-argcomplete` registers against (works against
  `command -v my-kitty` resolution).
- `path_integration.py` already owns the sentinel-bracketed rc block
  with `# >>> my-kitty PATH >>>` markers. The splice helpers
  (`_find_block`, `_splice_lines`) are content-agnostic — extending the
  block template is a render-time change, not a parser change.
- Single user is on zsh; bash is the fallback. argcomplete handles both
  via the same eval line (the helper detects from `$0`); fish would
  need a separate code path and is out of scope.

## Goals / Non-Goals

**Goals:**

- `my-kitty <TAB>` expands to the six subcommands.
- `my-kitty uninstall --keep<TAB>` expands to `--keep-backups
  --keep-config --keep-kitty`.
- `my-kitty prune --<TAB>` expands to the prune flag set.
- A single `make install` on a host running the OLD PATH-only block
  rewrites the block in place to include the new completion line. Same
  sentinel markers; no second migration window.
- `my-kitty doctor` reports an 8th check (`completion`) PASS/FAIL.
- Zero new test infrastructure: existing unit-test patterns cover all
  three module changes; integration coverage is opt-in.

**Non-Goals:**

- Fish completion. Single user runs zsh + bash; can be added later if
  surfaced.
- Static `_my-kitty` zsh completion file under `~/.zsh/completions/`.
  Static drifts; argcomplete reads from the live parser.
- COMP_WORDBREAKS surgery. Default behavior covers our flag set
  (no `:` or `=` in our flag values).
- Setup-time validation that argcomplete is importable. The dep is
  declared; uv resolves it at `uv tool install`. Doctor catches the
  rc-line drift case post-install.
- Auto-eval into a separate completion-only rc snippet (e.g.
  `~/.bash_completion.d/`). Keep one block, one home, sentinel-bracketed.

## Decisions

### D1 — Use `argcomplete` over a hand-rolled `_my-kitty` zsh function

argcomplete reads from the live argparse parser; static completion files
drift the moment a flag/subcommand is added or removed. The `keys`
subcommand was added two changes ago; `prune` one before that;
`--keep-*` flags landed last week. Three subcommand-surface changes in
two weeks. A static file would have rotted three times by now.

**Alternative considered:** generate a `_my-kitty` zsh file at install
time from the parser tree, regenerate on every `make install`. Rejected
— more code, same staleness risk between install runs, no bash
support without a second generator.

**Alternative considered:** ship a static `_my-kitty` checked into the
repo. Rejected — drift surface; user has to remember to run a
regenerator after every CLI edit.

### D2 — Single eval line in the existing sentinel block, not a separate completion block

The rc-file footprint stays one sentinel-bracketed block. Adding a
second block would double the surface area we have to clean up at
uninstall (the "PATH cleanup" line in `_SELF_REMOVAL_BANNER` would have
to mention two ranges). Splicing `register-python-argcomplete` into the
existing block keeps uninstall unchanged.

**Alternative considered:** drop a `~/.bash_completion.d/my-kitty` file
that the shell auto-sources. Rejected — bash-only convention; zsh
needs `fpath` + autoload not auto-source; doesn't unify the two
shells in one line.

### D3 — Wrap the eval in `command -v register-python-argcomplete >/dev/null 2>&1`

The dep is installed inside the `kitty-setup` uv tool venv. The
`register-python-argcomplete` shim is exposed at `~/.local/bin/` (uv
tool's standard exposed-bin path) → on PATH after the existing PATH
export line. But during the brief window between an `uv tool uninstall
my-kitty` (manual self-removal) and the user's next `make install`,
the shim disappears. Without the guard, every new shell would print
`command not found: register-python-argcomplete` on rc-source. The
guard makes the eval a no-op when the helper isn't there.

**Alternative considered:** unconditional eval, accept the noise during
the uninstall-then-reinstall window. Rejected — single line of friction
greets every new shell during the upgrade window; cheap to dodge.

**Alternative considered:** wrap with `if [[ -f ~/.local/bin/register-python-argcomplete ]]`.
Rejected — `command -v` is the portable POSIX idiom; `-f` ties us to
the uv-managed bin path.

### D4 — Block migration is pure render-replace; no version field

The existing `path_integration` splice helper finds the block by
sentinel markers and rewrites the bracketed lines from the current
template. No "block version" attribute is needed: the markers are the
contract, the body is regenerated each install. Hosts on the old
PATH-only block get the new content on the next `make install`.

**Alternative considered:** introduce a `# kitty-setup-block-version: 2`
comment line so we can detect old blocks and migrate explicitly.
Rejected — splice helpers already handle "block exists, replace
contents"; a version field is engineering for a problem we don't have.

### D5 — Doctor check name is `completion`, not `argcomplete`

The check is shell-facing, not implementation-facing. A user reading
`PASS completion: ...` understands; `PASS argcomplete: ...` leaks the
backing library name. If we ever swap argcomplete for a hand-rolled
generator (D1's rejected alternatives), the doctor key stays the same.

### D6 — Magic comment in cli.py, not in pyproject's `[tool.argcomplete]`

argcomplete also supports a `[tool.argcomplete]` section in pyproject
that lists global completion-enabled scripts. Adding the
`# PYTHON_ARGCOMPLETE_OK` magic comment to `cli.py` is the simpler path
— the `register-python-argcomplete` helper opens the script and grep
for the comment, no second config file involvement. Single source of
truth: the file with the parser.

## Risks / Trade-offs

* **Risk: argcomplete major version bumps break the eval line.** →
  *Mitigation:* pin to `>=3.5,<4` in `pyproject.toml`. uv lockfile
  freezes the exact resolved version. CI runs `uv tool install --force
  --reinstall .` regularly via `make install`; a 4.x release would
  surface immediately.
* **Risk: register-python-argcomplete shim path differs across uv
  versions.** → *Mitigation:* `command -v` resolves whatever PATH
  exposes; the rc block does not hard-code the path. uv tool versions
  >= 0.4 (current) all expose tool-provided binaries via `~/.local/bin`.
* **Risk: completion delays shell startup.** → *Mitigation:* the eval
  runs `register-python-argcomplete my-kitty` once per shell-init. On
  the user's hardware the helper finishes in ~30ms (probe-shellinit
  baseline from argcomplete docs). Below the perception threshold.
* **Risk: zsh users without `bashcompinit` get nothing.** →
  *Mitigation:* argcomplete's eval emits a zsh-native completion path
  for zsh sessions (auto-detected via `$0`). Manual `bashcompinit` is
  not required. README's "Updates" section documents the one-line
  fallback for the rare custom-zsh case.
* **Trade-off: one new PyPI dep.** Single-user repo; argcomplete is
  pure Python (no native deps), pinned, and tier-1 maintained
  (https://github.com/kislyuk/argcomplete, ~7M monthly downloads).
  Cost-of-dep is negligible against the user-experience win.

## Migration Plan

1. Land the four code commits + the docs commit + archive.
2. User runs `make install` (or `git pull && make install`). uv resolves
   the new `argcomplete` dep; `path_integration.ensure_local_bin_in_path()`
   rewrites the existing sentinel block in place to include the eval
   line. No new file appears anywhere; existing block grows by ~3 lines.
3. User opens a new shell (or sources their rc). `my-kitty <TAB>` works.
4. `my-kitty doctor` reports 8/8 PASS (assuming the
   `ctrl+shift+-` collision is also fixed by then; otherwise 7/8 with
   `bindings` failing as before).

Rollback: revert the change set. The `path_integration` template
regenerates without the eval line; the block re-shrinks on the next
`make install`. argcomplete dep is removed from `pyproject.toml`; uv
tool venv shrinks accordingly. No filesystem state is left behind that
the new uninstall flow doesn't already remove.

## Open Questions

* **Q1 — Should we extend the doctor `completion` check to drive a
  bash subprocess and assert tab-completion actually works
  end-to-end?** Pressure point: rc-line presence + helper resolvability
  is necessary but not sufficient — a malformed completion script
  would pass both checks but fail at the first `<TAB>`. *Default
  decision:* no, the integration test (gated by KITTI_INTEGRATION=1)
  covers the end-to-end path. Doctor stays cheap and synchronous.
* **Q2 — Should `simplify-uninstall-defaults` be amended (now archived)
  to ALSO clean up the new completion line on uninstall?** The block
  is removed wholesale by uninstall already (sentinel-marker-based);
  adding a line inside the block doesn't change the strip behavior.
  *Default decision:* no amendment needed. The block-strip is
  content-agnostic; current behavior covers the new content.
* **Q3 — Hosts that pin a non-uv Python (e.g. system python3 with
  shebang line drift) might miss the magic comment scan if
  argcomplete's helper is older than 3.5.** *Default decision:* the
  `>=3.5` floor covers the magic-comment scan path the helper uses
  today. If a user pins below that floor manually, the eval is a no-op
  rather than an error.
