## 1. Pre-flight

- [x] 1.1 Confirm `consolidate-into-my-kitty-setup-cli` has committed + archived. This change extends `cli.py` and assumes the single `my-kitty-setup` entry exists. If consolidate is still active, complete it first.
- [x] 1.2 Confirm `my-kitty-setup --help` lists 4 subcommands (install, uninstall, doctor, help). The new `prune` subcommand will become the 5th.

## 2. Backup listing helper

- [x] 2.1 Add `list_backups(conf_file: Path) -> list[Path]` to `src/kitty_setup/config_updater.py`. Returns all `kitty.conf.bak.YYYYMMDDTHHMMSSZ` files in `conf_file.parent`, sorted lexicographically (oldest first). Filter via the strict regex `r'^kitty\.conf\.bak\.\d{8}T\d{6}Z$'` per design D4 + risk #3 — anything else in the directory is invisible to the helper.
- [x] 2.2 Refactor `_latest_backup` to call `list_backups` and return the last element (or None). Keeps the behavior identical, removes duplication.
- [x] 2.3 Extend `tests/unit/test_config_updater.py` with cases: empty directory → []; mixed files (one bak + one user file) → only the bak; malformed bak filename → excluded; sort order (multiple baks) deterministic.

## 3. Pruner module

- [x] 3.1 Create `src/kitty_setup/pruner.py` with helpers:
  - `_describe(path: Path) -> tuple[str, datetime, int]` — name, mtime UTC, size.
  - `prune_by_keep(backups: list[Path], n: int) -> list[Path]` — return paths to delete (everything except the last n by filename order).
  - `prune_by_age(backups: list[Path], days: int, now: datetime | None = None) -> list[Path]` — return paths whose mtime is older than `days` days from `now` (default `datetime.now(UTC)`).
  - `prune_all(backups: list[Path]) -> list[Path]` — return the full list.
  - `delete_each(paths: list[Path]) -> int` — unlink each (ignoring FileNotFoundError to be robust against concurrent runs), return count actually deleted.
- [x] 3.2 Add `cli_prune(args: argparse.Namespace) -> int` handler to `pruner.py`. Logic:
  - Resolve target dir from `config_updater.ConfigPaths.for_user()`.
  - Call `config_updater.list_backups`.
  - If `not args.backups` (default dry-run): print listing + summary, exit 0.
  - If `args.backups`: choose policy — exclusive group of `--keep` / `--older-than` / `--all`. Default when only `--backups` is passed: keep=3.
  - Print "would delete" preview lines, call `delete_each`, print summary, exit 0.
  - Empty directory: print "no backups under <path>" and exit 0.

## 4. CLI wiring

- [x] 4.1 Register `prune` subparser in `src/kitty_setup/cli.py`. Mutually exclusive group for the three policy flags. `--keep` accepts an int (default 3, but only takes effect when `--backups` is set). `--older-than` accepts an int day count. `--all` is a store_true. The `--backups` flag is its own argument (action=store_true) gating the deletion path.
- [x] 4.2 Wire the subparser to `pruner.cli_prune` via `set_defaults(func=...)` matching the existing pattern.
- [x] 4.3 Verify `my-kitty-setup help` and `my-kitty-setup --help` both list `prune`.

## 5. Tests

- [x] 5.1 Author `tests/unit/test_pruner.py` covering:
  - Dry-run on empty dir → "no backups" message, exit 0, no writes.
  - Dry-run on populated dir (3 baks) → lists each, summary line, exits 0, files survive.
  - `--backups` (no policy) on 7 baks → keeps 3, deletes 4, exit 0.
  - `--backups --keep 1` on 4 baks → keeps newest 1, deletes 3.
  - `--backups --older-than 30` on baks with synthetic mtimes (use `os.utime`) at 5/20/40/60 days → deletes 2, keeps 2.
  - `--backups --all` on 5 baks → deletes all 5.
  - `--backups --keep 3 --older-than 30` simultaneously → exit non-zero, error mentions exclusive group, no deletions.
  - Directory with one bak + one unrelated file → bak handled, unrelated file untouched.
  - Directory with malformed bak (`kitty.conf.bak.notadate`) → excluded entirely.
- [x] 5.2 Author `tests/unit/test_cli_prune.py` (or extend existing test_cli.py): `prune` subparser routes to `pruner.cli_prune`; `prune --backups --keep N` populates args correctly; the help banner lists `prune`.

## 6. Makefile + docs

- [x] 6.1 Add `prune` Makefile target wrapping `my-kitty-setup prune --backups --keep 3`. Add to `.PHONY` and to the `help` target's echo list. Keep ≤ 5 lines.
- [x] 6.2 Update `README.md` quickstart to include `make prune` (recommended policy) and a one-line note about `my-kitty-setup prune --backups --older-than DAYS` / `--all` for non-default policies. Add a one-line note explaining "prune is opt-in; install/uninstall never delete backups".
- [x] 6.3 Update the rendered `prune` help text to mention the safety implication: pruning `--all` immediately before an install reduces rollback safety to the same-process backup. (One sentence in the subparser help description.)

## 7. Verify

- [x] 7.1 Run `make uninstall && make install` to seed at least one fresh backup. Confirm `~/.config/kitty/kitty.conf.bak.<ts>` exists.
- [x] 7.2 Run `my-kitty-setup prune` (no flags) — expect a one-line listing + summary, exit 0.
- [x] 7.3 Manually create 5 fake backups via `for i in 1 2 3 4 5; do touch ~/.config/kitty/kitty.conf.bak.20260101T00000${i}Z; done`. Run `my-kitty-setup prune --backups --keep 2` — expect 3 deletions, 2 survivors.
- [x] 7.4 Run `make prune` — expect "no backups" or "0 deletions" since the previous step normalised the count.
- [x] 7.5 Run `KITTI_INTEGRATION=1 make test` — expect all unit + integration tests pass, including the new `tests/unit/test_pruner.py` and `test_cli_prune.py` cases.
- [x] 7.6 Run `openspec validate add-backup-pruning --strict` — expect "Change is valid".

## 8. Commit + archive

- [ ] 8.1 Two commits: `feat(prune): add my-kitty-setup prune subcommand with --keep / --older-than / --all` (pruner.py + cli.py + config_updater list_backups + tests), `docs(prune): document make prune + opt-in semantics in README` (Makefile + README + help text touch-ups).
- [ ] 8.2 `openspec archive add-backup-pruning -y` — syncs the ADDED requirement into `openspec/specs/kitty-config-management/spec.md`.
- [ ] 8.3 Confirm `openspec list` shows `add-backup-pruning` archived; remaining active changes (if any) are still listed.
