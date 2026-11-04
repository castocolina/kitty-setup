## 1. Rename `[project.scripts]` entry + Python constants

- [x] 1.1 Update `pyproject.toml`: replace `my-kitty-setup = "kitty_setup.cli:main"` with `my-kitty = "kitty_setup.cli:main"`. Run `uv sync` so the local `.venv` reflects the new entry.
- [x] 1.2 Update `src/kitty_setup/cli.py`: change `PROG: str = "my-kitty-setup"` → `PROG: str = "my-kitty"`. Update the module docstring's mention of the entry point.
- [x] 1.3 Update `src/kitty_setup/installer.py` `_SELF_REMOVAL_BANNER`: replace the literal `uv tool uninstall my-kitty-setup` with `uv tool uninstall my-kitty`. Update the marker text in the same banner from `# >>> my-kitty-setup PATH >>>` to `# >>> my-kitty PATH >>>`.
- [x] 1.4 Update the inline probe-04 reference comment in `installer.py` to use the new banner text (the probe finding still applies — only the printed command changes).

## 2. Sentinel marker rename in `path_integration`

- [x] 2.1 Update `src/kitty_setup/path_integration.py`: rename `MARKER_BEGIN` constant from `# >>> my-kitty-setup PATH >>>` to `# >>> my-kitty PATH >>>`. Same for `MARKER_END`. Add private `_LEGACY_MARKER_BEGIN` and `_LEGACY_MARKER_END` constants holding the OLD strings — used only by the migration path.
- [x] 2.2 Add `_find_legacy_block(rc_text: str) -> tuple[int, int] | None` helper returning `(begin_idx, end_idx_exclusive)` for the first legacy marker block found in `rc_text` (line-index basis), or `None`. Mirror the shape of the existing block-finding logic in `config_updater._find_block`.
- [x] 2.3 Extend `ensure_local_bin_in_path` to handle three migration cases per design D2:
  - Legacy block present, new block absent → rewrite marker lines in place (preserve `export` line); return `PathEditResult(changed=True, reason="migrated legacy marker")`.
  - Both legacy and new blocks present → strip legacy block (markers + the line between them), keep new block; return `PathEditResult(changed=True, reason="removed duplicate legacy marker")`.
  - Neither legacy nor new block present, `~/.local/bin` not on `$PATH` → existing append-new-block behavior, unchanged.
- [x] 2.4 The "already configured" detection (rc has new marker block OR rc has user-authored export OR current process env has it) MUST run BEFORE the migration path. If new marker block already exists alone, no rewrite happens (idempotent).

## 3. Legacy shim detection in `cli_install`

- [x] 3.1 In `src/kitty_setup/installer.py` `cli_install`, after `_print_install_report` and `_print_path_result`, check whether `~/.local/bin/my-kitty-setup` exists. If so, print the migration notice on stdout per design D3:

```
legacy:        ~/.local/bin/my-kitty-setup detected; remove it with:
                   uv tool uninstall my-kitty-setup
```

  Non-fatal. Do NOT auto-remove. The check uses `Path.is_file()` or `Path.is_symlink()` (both — uv tool installs are symlinks).
- [x] 3.2 If the legacy shim is absent, print nothing (no "legacy: not detected" noise).

## 4. Bootstrap shell layer

- [x] 4.1 Update `tools/setup.sh`: change every `${HOME}/.local/bin/my-kitty-setup` reference to `${HOME}/.local/bin/my-kitty`, change `my-kitty-setup install` to `my-kitty install`, update the log strings.
- [x] 4.2 Update `tools/uninstall.sh` `resolve_binary`: prefer `my-kitty` (PATH lookup, then `~/.local/bin/my-kitty`), fall back to `my-kitty-setup` (PATH lookup, then `~/.local/bin/my-kitty-setup`). Log which one was picked. The fallback covers users who upgraded source but have not yet re-run `make install`.

## 5. Makefile

- [x] 5.1 Update every `my-kitty-setup ...` invocation in the Makefile to `my-kitty ...` (clean target, doctor target, prune target, help echo lines that quote command examples).
- [x] 5.2 Update the `uninstall ALL=1` help line to mention `my-kitty self-removal` instead of `my-kitty-setup self-removal`.

## 6. Tests

- [x] 6.1 Update `tests/unit/test_cli.py`: every literal `my-kitty-setup` in help-banner expectations and PROG references → `my-kitty`. Verify the new `prune` subcommand stays in the banner.
- [x] 6.2 Update `tests/unit/test_path_integration.py`: existing tests that write the marker block use the new constants automatically (they import `path_integration.MARKER_BEGIN` etc.). Add new cases:
  - `test_migrates_legacy_marker_alone`: rc with only legacy block → rewritten in place; assert markers are new form, export line byte-identical, result `changed=True, reason` contains "migrated legacy marker".
  - `test_migrates_legacy_with_unrelated_content`: rc with legacy block + user lines → migrated; user lines untouched.
  - `test_legacy_and_new_blocks_keep_new`: rc with both → legacy stripped, new kept; result `reason` contains "removed duplicate".
  - `test_idempotent_after_migration`: run twice; second run reports "already configured" and no further change.

## 7. Docs

- [x] 7.1 Update `README.md`: every `my-kitty-setup` literal in quickstart, Backup hygiene, Updates, Stack and layout sections → `my-kitty`. Add a one-paragraph note in the Updates section: "If you upgraded from the `my-kitty-setup` era, the install prints a one-line notice with the `uv tool uninstall my-kitty-setup` command — run it to clean up the legacy shim. Your shell rc PATH block migrates automatically."
- [x] 7.2 Update `CLAUDE.md` Stack paragraph: the single `[project.scripts]` entry is now `my-kitty`. The bash boundary now also includes the legacy-binary fallback in `tools/uninstall.sh`.
- [x] 7.3 Update `docs/agent-iteration.md` and `docs/probe-template.md`: no edits needed (no binary-name references; verify with grep).

## 8. Verify

- [x] 8.1 Run `uv run pytest tests/` — expect all unit tests pass with the renamed PROG and the new migration cases. Aim ≥ 80 tests (76 pre-rename + at least 4 new path_integration migration cases).
- [x] 8.2 Run `uv tool uninstall my-kitty-setup` to remove the legacy shim from this developer box, then `make install` end-to-end. Confirm `~/.local/bin/my-kitty` exists, `~/.local/bin/my-kitty-setup` does NOT, and the install output includes "PATH: migrated legacy marker" (assuming the rc block is the legacy form at upgrade time).
- [x] 8.3 Run `my-kitty doctor` — expect 6/6 PASS, exit 0.
- [x] 8.4 Run `my-kitty prune` (no flags) — expect dry-run listing, exit 0.
- [x] 8.5 Source-deletion check: `mv repo /tmp/x; cd /tmp; my-kitty doctor; mv /tmp/x repo`. Doctor must exit 0 with the source repo not at its original path.
- [x] 8.6 Inspect `~/.zshrc` after the upgrade install: confirm exactly one PATH block with the new marker form, and no legacy markers anywhere in the file.
- [x] 8.7 Run `KITTI_INTEGRATION=1 make test` — expect all unit + integration tests pass.
- [x] 8.8 Run `openspec validate rename-cli-to-my-kitty --strict` — expect "Change is valid".

## 9. Commit + archive

- [ ] 9.1 Two commits:
  - `feat(cli): rename my-kitty-setup binary to my-kitty` (pyproject + cli.py + installer.py + path_integration.py + Makefile + tools/setup.sh + tools/uninstall.sh + tests).
  - `docs: update README + CLAUDE.md for the my-kitty rename`.
- [ ] 9.2 `openspec archive rename-cli-to-my-kitty -y` — applies the REMOVE deltas (deletes `openspec/specs/my-kitty-setup-cli/`) and the ADD deltas (creates `openspec/specs/my-kitty-cli/`).
- [ ] 9.3 Confirm `openspec list` shows only `phase1-binding-introspection` (parked) as active.

## 10. Hand-off back to phase1-binding-introspection

- [ ] 10.1 Re-target the parked change: every `my-kitty-setup` reference in proposal/design/specs/tasks → `my-kitty`. Capability spec target moves from `specs/my-kitty-setup-cli/spec.md` → `specs/my-kitty-cli/spec.md`. Subcommand stays `keys`.
- [ ] 10.2 Resume the apply phase of `phase1-binding-introspection` per its retargeted tasks.md.
