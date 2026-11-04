---
created: 2026-11-04
source: Phase 2 close — 02-GAP-CODE-REVIEW.md (0 BLOCKER, 0 HIGH, 3 MEDIUM, 11 LOW) and the secure-phase audit (SECURED; unregistered flags U-1..U-3, advisory A-7)
suggested_phase: 5 (Component Separation) or a quick task before Phase 3 — none blocks Phase 2 close
---

# Phase 2 gap-review follow-ups

None of these blocked Phase 2 close (no BLOCKER/HIGH). Each needs the usual hypothesis →
experiment → decide before code changes (AGENTS.md).

## MEDIUM (code review)

- **WR-01 / U-2 — non-atomic rewrites of user files.** `path_integration.py:171` (`_write_rc`,
  bare `write_bytes`), `config_updater.py:460` and `:511` rewrite `~/.bashrc`, `~/.zshrc` and
  `kitty.conf` in place; ENOSPC/EIO or a kill mid-write leaves a truncated file, and the rc has no
  backup. A full uninstall also deletes the conf backups before rewriting `kitty.conf`. Fix: write a
  sibling of the *resolved* path, then `os.replace` (keeps a dotfiles symlink). The Phase-2 close
  install was protected by full copies + a sha256 bracket instead.
- **WR-02 — uninstall restores an older backup.** `_latest_backup` (`config_updater.py:201`) skips
  every block-bearing backup, so newer user content is dropped (probe: restored the January
  `font_size 10` backup over the June `font_size 14` one). Fix: restore the newest backup with our
  block stripped.
- **WR-03 — doctor false zsh PASS.** `doctor.py:293` does not check that `~/.local/share` is
  group/world-writable, which h41 rows C8/C9 show breaks registration and makes a later `compinit`
  prompt on every shell start; the PASS text says "one shape" breaks it while the README names two.

## Security audit flags (low, non-blocking)

- **U-1 — completion file mode not hardened.** `write_completion_script` (`installer.py:394-396`)
  writes `_my-kitty` / `my-kitty-completion.bash` under the umask and keeps an older file's mode;
  T-2-88 clears go-w on the directory only. On a host without per-user groups and umask 002 a group
  member could edit sourced shell code. Fix: clear go-w on the file after the write. (This host has
  umask 0022 + a user-private group, so not exploitable here.)
- **U-3 — unit guard fail-open edges.** Unaudited `os.link`/`os.truncate`/`os.chown`/`os.utime`/
  `os.system`/`socket.sendto|bind`; `shutil.rmtree` `dir_fd` ignored; process-global `_BUSY`;
  non-Index/Type/ValueError inside `_check` not recorded; roots from `$HOME` at import; only
  function-scoped tests guarded; `/tmp/kitty` (live kitty socket) is not a root.
- **A-7 — plan-only gates.** The conf-codec AST gate (T-2-51), rc-I/O AST gate (T-2-62), launcher
  payload AST gate (T-2-58, VALIDATION 02-04-T1) and the guard negative control (T-2-54) exist only
  in plans/VALIDATION; port them into `tests/unit/` as A-2 was.

## LOW (code review, one line each — details in 02-GAP-CODE-REVIEW.md)

Overlapping legacy+current blocks can delete an rc line; a broken-symlink `kitty.conf` is unlinked
on a failed install; `kitty.conf` loses CRLF; doctor passes duplicate blocks install then rewrites;
runner ignores `--` and never checks its pytest option list against the installed pytest; child-env
AST rule covers a fixed module list (the bandit test's child inherits the real env); removing the
B310 skip left the download invisible to both linters and the `pyproject.toml` comment is stale;
the integration sandbox passes `KITTY_*_DIRECTORY` and `BASH_ENV` through; small dead code /
duplication and one garbled docstring; two error paths still end in a traceback.

## Also noted during execution

- The integration runner left three empty `/tmp/kitti-integration-*` dirs after 02-12's runs
  (not reproduced in 02-13..02-15); worth a cleanup assertion in the runner.
- 02-12-SUMMARY.md lacks `plan_head_before/after` (the commit ledger was never written).
