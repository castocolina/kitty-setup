## 1. Pre-flight

- [x] 1.1 Confirm the four prior changes (`consolidate-into-my-kitty-setup-cli`, `add-backup-pruning`, `rename-cli-to-my-kitty`, `phase1-binding-introspection`) are archived. `openspec list` should show no active changes other than this one before apply starts.
- [x] 1.2 Confirm `my-kitty uninstall --help` currently lists `--kitty` and `--self` (the pre-rename surface). After this change, neither flag survives; their absence is the verification.

## 2. CLI surface (cli.py)

- [x] 2.1 In `src/kitty_setup/cli.py`, replace the two existing `--kitty` and `--self` arguments under the `uninstall` subparser with three new `--keep-*` arguments:
  - `--keep-backups` (action=store_true, dest=keep_backups)
  - `--keep-config` (action=store_true, dest=keep_config)
  - `--keep-kitty` (action=store_true, dest=keep_kitty)
- [x] 2.2 Update the subparser `description` to summarise the new defaults: "Remove our entire footprint by default. Use --keep-* flags to preserve specific subsets."
- [x] 2.3 Drop any references to `args.self_` / `args.kitty` in the uninstall handler dispatch. The new args are `args.keep_backups`, `args.keep_config`, `args.keep_kitty`.

## 3. Uninstall handler (installer.py)

- [x] 3.1 Rewrite `cli_uninstall` to use the new flag set. Logic:
  - Compute three booleans: `do_config = not args.keep_config`, `do_backups = not args.keep_config and not args.keep_backups` (backups are inside the config-side surface, so keep_config also keeps backups), `do_kitty = not args.keep_kitty`.
  - If `do_config`: call `uninstall_config_only()` (today's `config_updater.uninstall(paths)`); print the result lines like today.
  - If `do_backups`: list backups via `config_updater.list_backups(paths.conf_file)`, then `pruner.delete_each(...)` to nuke. Print a single summary line `backups: deleted N file(s)` or `backups: nothing to delete`.
  - If `do_kitty`: call `remove_kitty_install()` (today's helper); print the result lines like today.
  - At the end, ALWAYS print `_SELF_REMOVAL_BANNER` (no longer gated by `--self`).
- [x] 3.2 Update `_SELF_REMOVAL_BANNER`: prefix it with a friendly intro like `binary:        the my-kitty binary itself was NOT removed. To remove it:` so the always-on banner reads naturally regardless of preceding flag set. Keep the literal `uv tool uninstall my-kitty` command + the `# >>> my-kitty PATH >>>` marker reference.
- [x] 3.3 Drop the `--self` / `--kitty` argument handling from `cli_uninstall`. The function signature is unchanged (it still takes `argparse.Namespace`).

## 4. Bash dispatcher (tools/uninstall.sh)

- [x] 4.1 Rewrite `tools/uninstall.sh` confirm prompt. Logic:
  - Read `KEEP_BACKUPS`, `KEEP_CONFIG`, `KEEP_KITTY` env vars (default empty).
  - Build the `UNINSTALL_FLAGS` string from the env vars (e.g. `--keep-backups --keep-kitty`).
  - Compute the "will remove" enumeration locally in bash from the same env vars; print it line-by-line.
  - Drop the always-on "Backups under ~/.config/kitty/kitty.conf.bak.* will be kept" line entirely.
  - The "After this completes, run `uv tool uninstall my-kitty`" footer stays.
- [x] 4.2 Test the prompt against four flag combinations (no flags, KEEP_BACKUPS=1, KEEP_CONFIG=1, KEEP_KITTY=1). The prompt should enumerate exactly the items that WILL be touched.

## 5. Makefile

- [x] 5.1 Replace the `UNINSTALL_FLAGS := $(if $(filter 1,$(ALL)),--kitty --self,)` line with a composite `KEEP` flag-builder:
  ```
  UNINSTALL_FLAGS := \
      $(if $(filter 1,$(KEEP_BACKUPS)),--keep-backups,) \
      $(if $(filter 1,$(KEEP_CONFIG)),--keep-config,) \
      $(if $(filter 1,$(KEEP_KITTY)),--keep-kitty,)
  ```
- [x] 5.2 Update the `help` target's echo lines: drop the `uninstall ALL=1` line; add three new lines listing the `KEEP_BACKUPS=1` / `KEEP_CONFIG=1` / `KEEP_KITTY=1` knobs each with a one-line description.
- [x] 5.3 The `uninstall:` target body stays one line (`./tools/uninstall.sh` with the env passed through).

## 6. Tests

- [x] 6.1 Update `tests/unit/test_cli.py` — replace the `test_uninstall_routes_to_cli_uninstall_with_flags` and `test_uninstall_default_scope_no_flags` cases with the new flag set:
  - default: all three `keep_*` are False
  - each `--keep-*` flag flips its respective bool to True
  - all three flags compose
  - legacy `--kitty` / `--self` cause SystemExit non-zero (argparse rejects them)
- [x] 6.2 Author `tests/unit/test_installer_uninstall.py` covering `cli_uninstall` per `--keep-*` combination. Use monkeypatch to replace `uninstall_config_only`, `config_updater.list_backups`, `pruner.delete_each`, `remove_kitty_install` with synthetic fakes that record their invocations. Assertion shape: each combination of `keep_*` flags drives the expected subset of helper invocations.
- [x] 6.3 Update `tests/unit/test_path_integration.py` — no change needed (PATH integration is unaffected). Verify with a no-op test run.

## 7. Documentation

- [x] 7.1 Update `README.md`:
  - Quickstart: replace `make uninstall` line and the `make uninstall ALL=1` line with the new shape (`make uninstall` is now aggressive; document `KEEP_*=1` knobs).
  - Add a paragraph in the "Updates" section: "**Breaking change as of simplify-uninstall-defaults**: `make uninstall` now removes everything by default. The legacy config-only behavior is `make uninstall KEEP_KITTY=1 KEEP_BACKUPS=1`."
- [x] 7.2 Update `CLAUDE.md`: the Stack paragraph mentions the bash boundary covers "a thin confirm + flag-forward layer over `my-kitty uninstall`". Adjust wording if the new flag-forward logic in tools/uninstall.sh outgrows "thin"; if it stays one-screen, leave the wording.
- [x] 7.3 No changes to `docs/agent-iteration.md` or `docs/probe-template.md` (no probe-vs-hypothesis impact).

## 8. Verify

- [x] 8.1 Run `uv run pytest tests/` — expect ≥ 105 unit tests pass (today's count plus the new `test_installer_uninstall.py` cases).
- [x] 8.2 Run `KITTI_INTEGRATION=1 uv run pytest tests/` — expect all integration + unit tests pass.
- [x] 8.3 Run `uv tool install --force --reinstall .` to refresh the binary. Run `my-kitty uninstall --help` — expect the help banner to list `--keep-backups`, `--keep-config`, `--keep-kitty` and NOT list `--kitty` or `--self`.
- [ ] 8.4 End-to-end uninstall+install cycle:
  - Create a fake backup: `touch ~/.config/kitty/kitty.conf.bak.20260101T000000Z`.
  - Run `KITTI_FORCE=1 make uninstall`. Confirm: `~/.local/kitty.app/`, `~/.local/bin/kitty`, the desktop entry, `~/.config/kitty/kitty.conf` (block), `~/.config/kitty/kitty-setup/`, AND the synthetic backup are all gone.
  - Run `make install`. Confirm everything's back.
- [ ] 8.5 Run `KITTI_FORCE=1 make uninstall KEEP_BACKUPS=1` after creating a fake backup — confirm the backup survives.
- [ ] 8.6 Run `KITTI_FORCE=1 make uninstall ALL=1` (legacy knob) — confirm behavior is identical to no env var (the new default IS the aggressive scope; ALL=1 is silently ignored).
- [x] 8.7 Run `openspec validate simplify-uninstall-defaults --strict` — expect "Change is valid".

## 9. Commit + archive

- [ ] 9.1 Three commits:
  - `feat(uninstall): invert default scope; --keep-backups / --keep-config / --keep-kitty preserve subsets` (cli.py + installer.py + tools/uninstall.sh + Makefile + tests).
  - `docs: update README + CLAUDE.md for the new uninstall defaults` (docs).
  - `docs(openspec): archive simplify-uninstall-defaults` (after archive command).
- [ ] 9.2 `openspec archive simplify-uninstall-defaults -y` — applies the MOD deltas to `my-kitty-cli` and `kitty-config-management`.
- [ ] 9.3 Confirm `openspec list` shows zero active changes.
