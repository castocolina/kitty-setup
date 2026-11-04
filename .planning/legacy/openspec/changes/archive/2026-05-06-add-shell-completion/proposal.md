## Why

`my-kitty <TAB>` currently expands to nothing because plain argparse ships
no shell completion. The user surfaced this as a verbal ask after the
`simplify-uninstall-defaults` archive landed and noticed `my-kitty
uninstall --keep<TAB>` was silent. Tab completion is a baseline
expectation for any CLI carrying six subcommands and a half-dozen
flag-bearing surfaces — the gap reads as the binary being incomplete.

`argcomplete` is the standard one-line bolt-on for argparse: register
once in `main()`, drop one `eval` line into the user's shell rc, get
bash + zsh completion for free with the active subcommand/flag surface
introspected at completion time. No second source-of-truth to drift.

## What Changes

- Add `argcomplete>=3.5,<4` as a runtime dep in `pyproject.toml`.
- `src/kitty_setup/cli.py` registers the completion hook:
  - `# PYTHON_ARGCOMPLETE_OK` magic comment in the file's first ~1024 bytes.
  - `argcomplete.autocomplete(parser)` call in `main()` between
    `_build_parser()` and `parser.parse_args()`. In normal interactive
    runs it's a no-op (env-var guarded by argcomplete itself).
- `src/kitty_setup/path_integration.py` extends the sentinel-bracketed
  rc block to inject a guarded `eval "$(register-python-argcomplete
  my-kitty)"` line alongside the existing PATH export. Block migrates
  in place on the next `make install` for hosts running the
  PATH-only block.
- `src/kitty_setup/doctor.py` adds an 8th check, `completion`, that
  PASSes when (a) `register-python-argcomplete` resolves on PATH AND
  (b) the eval line is present inside the active sentinel block.
- README "Quickstart" gains a one-liner pointing at tab completion;
  README "Updates" notes that re-running `make install` migrates the
  PATH-only block to the new shape.

Breaking? **No** for users with no rc block yet; **transparent migration**
for users with the PATH-only block (the splice helper rewrites the block
content from a single template, same sentinel markers).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `my-kitty-cli`: MOD the existing `Single binary on PATH with subcommand
  dispatch` requirement to add the argcomplete registration step (CLI
  `main()` calls `argcomplete.autocomplete(parser)` before `parse_args`).
  MOD the existing `~/.local/bin is on PATH after install` requirement
  to extend the sentinel-bracketed shell-rc block content with the
  `register-python-argcomplete` eval line. ADD a new requirement
  `Doctor reports tab-completion health` that pins the new 8th doctor
  check.

## Impact

- **Edited files**: `pyproject.toml` (one new dep),
  `src/kitty_setup/cli.py` (magic comment + import + one call),
  `src/kitty_setup/path_integration.py` (block template extended;
  splice helper unchanged), `src/kitty_setup/doctor.py` (one new
  CheckResult function + wire into the dispatch list),
  `README.md` (quickstart + updates note).
- **New tests**: extend `tests/unit/test_cli.py`,
  `tests/unit/test_path_integration.py`, `tests/unit/test_doctor.py`.
- **New runtime dep**: `argcomplete>=3.5,<4`. Single-user repo; cost is
  negligible.
- **No probes required.** argcomplete is a battle-tested upstream lib;
  spec scenarios pin behavior without a probe round.
- **Out of scope** (separate follow-up changes if surfaced):
  - Static zsh `_my-kitty` completion file. argcomplete is the chosen
    path; static drifts as the subcommand surface evolves.
  - Fish completion. Single user is on bash + zsh today.
  - `tools/setup.sh` edits. Install path runs `my-kitty install` →
    `path_integration.ensure_local_bin_in_path()` already; no
    bootstrap-shell edit needed.
