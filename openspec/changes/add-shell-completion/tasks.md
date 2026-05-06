## 1. Pre-flight

- [ ] 1.1 Confirm `openspec list` shows zero active changes other than `add-shell-completion`. The previous change (`simplify-uninstall-defaults`) must be archived.
- [ ] 1.2 Confirm the current `~/.zshrc` (or `~/.bashrc`) sentinel block is the PATH-only shape. Capture before-state with `sed -n '/>>> my-kitty PATH >>>/,/<<< my-kitty PATH <<</p' ~/.zshrc` for comparison post-apply.
- [ ] 1.3 Confirm `argcomplete` is not yet listed in `pyproject.toml` `[project] dependencies`. If a stray entry exists, abort and reconcile.

## 2. Dependency

- [ ] 2.1 Add `argcomplete>=3.5,<4` to the `[project] dependencies` array in `pyproject.toml`. Keep alphabetical order if the existing list is alphabetical.
- [ ] 2.2 Run `uv lock` to refresh `uv.lock`. Verify the lock entry resolves a 3.x version.
- [ ] 2.3 Run `uv sync` to provision the dev `.venv` with the new dep. Verify `python -c "import argcomplete; print(argcomplete.__version__)"` succeeds inside `uv run`.

## 3. CLI surface (cli.py)

- [ ] 3.1 In `src/kitty_setup/cli.py`, add the literal line `# PYTHON_ARGCOMPLETE_OK` as a top-of-file comment within the first 1024 bytes (placed as line 2, immediately after the module docstring's terminating `"""`). The existing module docstring stays at line 1.
- [ ] 3.2 Add `import argcomplete` to the imports block. Order with the other third-party imports.
- [ ] 3.3 In `main()`, between `parser = _build_parser()` and `args = parser.parse_args(argv)`, add `argcomplete.autocomplete(parser)`. The call returns immediately when `_ARGCOMPLETE` is unset in env (interactive runs); short-circuits to candidate emission when set.
- [ ] 3.4 Verify `python -c "from kitty_setup.cli import main; import os; os.environ['_ARGCOMPLETE']='1'; main()"` does NOT crash and behaves as a completion request (argcomplete will print to fd 8 / fd 9; redirect to verify).

## 4. PATH integration (path_integration.py)

- [ ] 4.1 In `src/kitty_setup/path_integration.py`, locate the rc-block template constant (or function returning the block body). Extend it so the bracketed body is:
  ```
  if [ -d "$HOME/.local/bin" ] && [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
      export PATH="$HOME/.local/bin:$PATH"
  fi
  if command -v register-python-argcomplete >/dev/null 2>&1; then
      eval "$(register-python-argcomplete my-kitty)"
  fi
  ```
  The sentinel markers (`# >>> my-kitty PATH >>>` / `# <<< my-kitty PATH <<<`) are unchanged.
- [ ] 4.2 Verify the existing splice helpers (`_find_block`, `_splice_lines`, plus the migration logic for the legacy `my-kitty-setup` markers) still work — they are content-agnostic, so no change should be needed.
- [ ] 4.3 The "already configured" detection logic must require BOTH the PATH line AND the eval line to be present in the block to short-circuit. If only the PATH line is present (old block shape), the block must be rewritten with the new content.

## 5. Doctor (doctor.py)

- [ ] 5.1 In `src/kitty_setup/doctor.py`, add a new function `_check_completion()` returning a `CheckResult`. PASS condition: `shutil.which("register-python-argcomplete")` resolves AND the active rc file's sentinel block contains the literal substring `register-python-argcomplete my-kitty`.
- [ ] 5.2 FAIL message MUST distinguish the two failure modes: "register-python-argcomplete not on PATH" vs "completion eval line missing from rc block".
- [ ] 5.3 Wire `_check_completion` into the `cli_doctor` dispatch list as the 8th check (after `bindings`). The order convention is roughly install-then-config-then-runtime; completion is a runtime check.

## 6. Tests

- [ ] 6.1 In `tests/unit/test_cli.py`, add a test `test_main_invokes_argcomplete_autocomplete`. Monkeypatch `cli.argcomplete.autocomplete` to a recording fake; call `cli.main(["help"])`; assert the fake was called once with the parser instance.
- [ ] 6.2 In `tests/unit/test_path_integration.py`, add three tests:
  - `test_rc_block_contains_path_export_and_completion_eval`: render a fresh block; assert both lines present.
  - `test_old_path_only_block_migrates_in_place`: seed a tmpfile rc with the old PATH-only block shape between the current sentinel markers; run `ensure_local_bin_in_path()` against that path; assert the resulting block contains both lines AND the file's pre-block + post-block bytes are unchanged.
  - `test_already_configured_short_circuits_only_with_both_lines`: a block with PATH-only does NOT short-circuit; a block with both lines DOES short-circuit.
- [ ] 6.3 In `tests/unit/test_doctor.py`, add three tests for `_check_completion`:
  - `test_completion_check_passes_when_helper_and_rc_line_present`: monkeypatch `shutil.which` and the rc-file read; assert PASS.
  - `test_completion_check_fails_when_helper_missing`: helper absent; assert FAIL with the helper-specific message.
  - `test_completion_check_fails_when_rc_line_missing`: helper present but rc has PATH-only; assert FAIL with the rc-specific message.
- [ ] 6.4 Run `uv run pytest tests/unit/` — expect ≥ 117 unit tests pass (today's 111 + the 6 new ones).

## 7. Documentation

- [ ] 7.1 Update `README.md` Quickstart: add a one-liner under the install commands: `my-kitty <TAB>           # bash + zsh tab completion (after one make install)`.
- [ ] 7.2 Update `README.md` "Updates" section: a one-paragraph note that re-running `make install` migrates the PATH-only rc block to include the completion eval line, sentinel markers unchanged.
- [ ] 7.3 No changes to `CLAUDE.md` Stack paragraph (Bash boundary unchanged: still tools/setup.sh + tools/uninstall.sh; argcomplete eval is in user's rc, not in our scripts).

## 8. Verify

- [ ] 8.1 Run `uv run pytest tests/unit/ -q` — green, ≥ 117 passing.
- [ ] 8.2 Run `KITTI_INTEGRATION=1 uv run pytest tests/ -q` — all integration + unit tests pass.
- [ ] 8.3 Run `uv tool install --force --reinstall .` to refresh the deployable. Verify `command -v register-python-argcomplete` resolves under `~/.local/bin/` (uv-exposed bin path).
- [ ] 8.4 Run `make install`. Confirm:
  - `~/.zshrc` (or `~/.bashrc`) sentinel block now contains BOTH the PATH export AND the guarded `register-python-argcomplete my-kitty` eval line.
  - File bytes outside the sentinel block are byte-identical to the pre-install snapshot.
- [ ] 8.5 Open a fresh shell. Run:
  - `my-kitty <TAB>` → expects a candidate list including `install`, `uninstall`, `doctor`, `prune`, `keys`, `help`.
  - `my-kitty uninstall --keep<TAB>` → expects `--keep-backups`, `--keep-config`, `--keep-kitty`.
  - `my-kitty prune --<TAB>` → expects `--backups`, `--keep`, `--older-than`, `--all`.
- [ ] 8.6 Run `my-kitty doctor`. Confirm the new `completion` line PASSes (the `bindings` line may still FAIL on the unrelated `ctrl+shift+-` collision until the follow-up change lands).
- [ ] 8.7 Run `openspec validate add-shell-completion --strict` — expect "Change is valid".

## 9. Commit + archive

- [ ] 9.1 Three commits, in order:
  - `feat(completion): add argcomplete-driven bash + zsh tab completion` (pyproject.toml, uv.lock, cli.py, path_integration.py, doctor.py, all unit tests).
  - `docs: README quickstart + updates note for tab completion` (README.md only).
  - `docs(openspec): archive add-shell-completion, sync specs` (after archive command).
- [ ] 9.2 `openspec archive add-shell-completion -y` — applies the MOD + ADD deltas to `my-kitty-cli/spec.md`.
- [ ] 9.3 Confirm `openspec list` reports zero active changes.
