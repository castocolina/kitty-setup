---
phase: 02-defect-remediation
plan: 09
subsystem: quality-tooling, harness, path-integration, scenes
status: complete
tags: [R0.11, dead-code, contextlib-suppress, re-exports, mechanical]
requires: [02-07, 02-08, 02-11]
provides:
  - "`src/` black-clean; ruff down 6 → 2 (only the two S607 `02-10` owns); pyright `reportUnusedImport` 8 → 0 via an `__all__` re-export declaration in `scenes/__init__.py`; both SIM105 try-except-pass sites now `contextlib.suppress`; the RUF001 en dash replaced with a hyphen; the RUF100 unused `# noqa: S603` removed by `ruff --fix`"
  - "Four provably dead symbols deleted: `TARGET_DIR_REL` (+ its `__all__` entry), the `env_path` parameter of `ensure_local_bin_in_path` (+ 21 test call sites + the `fake_ensure` stub's copy), `KittySession.send_key` (+ its docstring advertisement), and the uncalled `_find_tab_with_window` in `tests/integration/test_h25_scene_launcher.py`"
  - "Residual inventory for `02-10`: ruff 2×S607, pyright 5×`reportPrivateUsage` + 1×`reportUnnecessaryComparison`, bandit 33 (0 high / 11 medium / 22 low), vulture 13 (`src`) / 8 under five allowlist names with fixtures set aside, 15 suppression comments still in `src/`"
affects: [02-10]
tech-stack:
  added: []
  patterns:
    - "a deliberate re-export module declares its names in `__all__` — pyright reads that, not ruff's `noqa`"
    - "a never-consulted back-compat kwarg is deleted together with every caller in one commit, not deprecated in place"
    - "`with`-statement exception suppression: `contextlib.suppress` replaces try-except-pass (SIM105), including at the U-1 teardown line whose verb and non-propagation are pinned by `tests/unit/test_harness_teardown.py`"
key-files:
  created:
    - .planning/phases/02-defect-remediation/02-09-SUMMARY.md
  modified:
    - src/kitty_setup/scenes/__init__.py
    - src/kitty_setup/scenes/_client.py
    - src/kitty_setup/cli.py
    - src/kitty_setup/path_integration.py
    - src/kitty_setup/harness/kitty_session.py
    - tests/unit/test_path_integration.py
    - tests/unit/test_installer_completion.py
    - tests/integration/test_h25_scene_launcher.py
    - tests/integration/test_h02_clear.py
decisions:
  - "RUF001: the en dash in cli.py's opacity help became a plain hyphen — a character a terminal user reads — rather than a ruff config entry declaring the typography deliberate; one character did not justify a config line"
  - "`scenes/__init__.py` uses the `__all__` form; it worked on the first try, so no fallback to `import x as x` was needed (measured with ruff and pyright per-file, not assumed)"
  - "RUF001 and both SIM105 sites were fixed by hand after `ruff --fix`, because only the RUF100 directive is auto-fixable (measured)"
  - "The research's triage of `send_key` (test-used) is corrected by measurement: no caller exists in src/, tests/ or tools/; the only mention outside its definition is a docstring explaining the test avoids it"
  - "`session_dir` was kept: dead at `bbed580`, read by `tests/unit/test_kitty_session_socket.py:60` and `:84` since 02-11's socket fix"
metrics:
  duration: "~50 min"
  completed: 2026-09-24
actuals:
  tokens: 21000
  tasks: 3
  commits: 1
plan_head_before: 1e9209aef20dae8fa6f0ec90f4912fbf0ba2bb52
---

# Phase 2 Plan 09: the mechanical half of R0.11 (summary)

R0.11 makes `src/` clean under black, ruff, pyright, bandit and vulture. This plan did the
half of that a formatter, an auto-fix, a mechanical edit, or a deletion of a provably-unused
symbol can close; `02-10` does the policy half (tool configuration with rationale in
`pyproject.toml`) and closes the requirement.

Scope anchor (pre-work `HEAD`): `1e9209a` (`Merge 02-08 (R1.6, R1.7): integration tests shed
KITTY_* env; prune --keep rejects negatives cleanly`), the tip of `gsd/phase-02-defect-remediation`,
branch `xai/02-09`. `core.hooksPath` read `tools/hooks` throughout. One commit, per the
commit-granularity rule and the plan's frontmatter `type: execute` (R0.11 adds no behaviour; there
is no RED test to write first).

## Step 0: the before-state, before any edit

`tmp/r011-sizing/` — `repro.md` (all tools' verbatim output plus per-symbol `rg` evidence),
`actual.json` (before/after counts), and the raw outputs `black-before.txt`, `ruff-before.txt`,
`pyright-before.txt`, `bandit-before.txt`, `vulture-{src,src-tests,fixtures}-before.txt` and
`-after.txt`, `symbol-evidence.txt`, `black-run.txt`, `ruff-fix-run.txt`,
`integration-after.txt`. The step-0 gate (the record exists and names all five tools' commands)
exited 0 before the first edit.

### Before (at `1e9209a`)

| Command | Exit | Result |
|---|---|---|
| `uv run black --check src` | 1 | 1 file would be reformatted (`scenes/_client.py`), 21 unchanged |
| `uv run ruff check src --output-format concise` | 1 | **6**: RUF001 `cli.py:338`, SIM105 `harness/kitty_session.py:322` and `:350`, S607 `installer.py:170`, RUF100 `scenes/_client.py:43`, S607 `scenes/_client.py:44` |
| `uv run pyright src` | 1 | **14 errors**: 8 `reportUnusedImport` (`scenes/__init__.py:6-13`), 5 `reportPrivateUsage`, 1 `reportUnnecessaryComparison` (`kitty_session.py:210`) |
| `uv run bandit -c pyproject.toml -q -r src` | 1 | **33 — 0 high / 11 medium / 22 low** |
| `uv run vulture src` | 3 | **15** findings |
| `uv run vulture src tests` | 3 | **15** findings |
| `uv run vulture --ignore-decorators '@pytest.fixture' src tests` | 3 | **12** findings |

Divergences from the plan's figures at `5925724`, stated rather than reconciled: the RUF001 en
dash moved `cli.py:321` → `:338` and the `fake_ensure` stub's `env_path` moved
`test_installer_completion.py:162` → `:164` (02-08's edits shifted lines above them); counts and
shapes are identical. `uv run vulture src` reports **15** where the plan recorded **16**: the
plan's arithmetic already discounted `path_integration.py`'s `reason` (removed by `02-07`), and
at `1e9209a` that finding is already gone, so the plan's "minus reason is 15" expectation is met
one step earlier than anticipated. The other two vulture scopes (15 and 12) match the plan.

## After (this plan's edits, before the commit)

| Command | Exit | Result |
|---|---|---|
| `uv run black --check src` | **0** | clean — 22 files unchanged |
| `uv run ruff check src --output-format concise` | 1 | **2**: S607 `installer.py:170`, S607 `scenes/_client.py:44` — exactly the pair the plan hands to `02-10` |
| `uv run pyright src` | 1 | **6 errors**: 5 `reportPrivateUsage`, 1 `reportUnnecessaryComparison` — `reportUnusedImport` **8 → 0** |
| `uv run bandit -c pyproject.toml -q -r src` | 1 | **33 — 0 high / 11 medium / 22 low** (unchanged: no subprocess shape was touched) |
| `uv run vulture src` | 3 | **13** findings |
| `uv run vulture src tests` | 3 | **11** findings |
| `uv run vulture --ignore-decorators '@pytest.fixture' src tests` | 3 | **8** findings, every one under the five names `02-10` allowlists |

## Task 1 — formatter, auto-fixer, and the three mechanical residuals

In the plan's order, each command's output captured under `tmp/r011-sizing/`:

1. `uv run black src` — reformatted exactly one file, `scenes/_client.py`, one hunk (the
   three-line `raise SceneClientError(...)` joined to one line). `ruff format` was **deliberately
   not run**: `.claude/conventions.md:44` excludes it, and black is the single source of truth
   for formatting.
2. `uv run ruff check src --fix` — fixed exactly one finding, the RUF100 unused
   `# noqa: S603` directive at `scenes/_client.py:43` (the plan predicted precisely this;
   nothing else in the six was auto-fixable). This also removed the one F401 suppression, so
   the removable `# noqa` left `src/` in this task.
3. `cli.py` RUF001: the en dash in the opacity help string (`0.0–1.0`) became a plain hyphen
   (`0.0-1.0`). The alternative — a ruff config entry declaring the typography deliberate — was
   rejected because a config line is not worth one character inside a help string a user reads
   on a terminal, where a hyphen is the right character anyway.
4. `kitty_session.py:322` and `:350` SIM105: both try-except-pass blocks are now
   `contextlib.suppress`. The `:322` site is U-1's teardown block: the verb stays
   `close-window --match=all` and `HarnessCommandError` still does not propagate. A first
   rewrite of `:350` produced nested `with` statements, which ruff flagged SIM117; collapsed to
   a single `with self._process, contextlib.suppress(ProcessLookupError):`.

The residual after task 1 is exactly what the plan's re-measured expectation said: the two S607
(`installer.py:170`, `_client.py:44`), a design call for `02-10`. Nothing else survived; no
divergence to reconcile.

### Task 1 gates

| Gate | Exit | Note |
|---|---|---|
| step-0 record exists and names all five tools (`tmp/r011-sizing/`) | 0 | |
| `uv run black --check src` | 0 | clean |
| ruff: no RUF001/E501/SIM105/RUF100 survives (whole-`src` form) | **red, exit 1** | `ruff check src` still exits 1 on the two S607; the four-shape half passes (recorded output above shows only S607). Red until `02-10` — recorded, not weakened |
| `contextlib.suppress` ×2, `close-window` present, `close-os-window` absent | 0 | |
| `uv run pytest tests/unit/test_harness_teardown.py -q` (run immediately after the rewrite) | 0 | 3 passed — the U-1 pin held through the refactor of its own lines |
| no suppression comment anywhere in `src/` | **red** | 15 lines still carry one (11× `# noqa`, 4× `# type: ignore[attr-defined]`); enumerated below. Red until `02-10` — recorded, not weakened |

*(The last two rows are the plan's "red until 02-10" gates; their outputs are recorded, their
verdicts are not claimed.)*

## Task 2 — the eight re-exports declared

`src/kitty_setup/scenes/__init__.py`: the `# noqa: F401` on the import block is gone; an
`__all__` listing all eight submodule names (`accent`, `background`, `colors`, `font`,
`launcher`, `opacity`, `recipe`, `title`) now declares the re-export. The explanatory comment at
`:3-4` (why the module re-exports at all) survives.

The `__all__` form worked on the first try — **no fallback to the explicit `import accent as
accent` form was needed**. Verified with both tools rather than assumed:

- `uv run ruff check src/kitty_setup/scenes/__init__.py` → clean (exit 0)
- `uv run pyright src/kitty_setup/scenes/__init__.py` → clean (exit 0)
- `uv run pyright src` → 6 errors, none `reportUnusedImport` (was 8 of 14)
- `uv run pytest tests/unit/test_cli.py -q` → **39 passed** — every `monkeypatch.setattr`
  target still resolves

## Task 3 — four dead symbols deleted, proven by the integration suite

Evidence each was dead against `src/`, `tests/` **and** `tools/` (`rg`, verbatim in
`tmp/r011-sizing/symbol-evidence.txt`, recorded before any edit):

1. **`TARGET_DIR_REL`** (`path_integration.py`): exactly two hits — its `__all__` entry and its
   definition; no reader anywhere. Both deleted together (leaving the entry would be
   `reportUnsupportedDunderAll`). Vulture had stopped reporting it because `02-02` listed it in
   `__all__` (an entry counts as a use), which is why its deletion is proven by `rg`, not by
   vulture.
2. **`env_path`** (`ensure_local_bin_in_path`): its own comment said "kept for kwarg
   back-compat; no longer consulted"; the only `src` caller (`installer.py`) passes no
   arguments. **Real call-site count: 21** in `tests/unit/test_path_integration.py` (twenty
   `env_path=""` and the `env_path=f"{target}:/usr/bin"` call), plus the parameter itself and
   the copy on the `fake_ensure` stub in `tests/unit/test_installer_completion.py`. The
   research's 15 and the earlier draft's 17 were both stale — `02-02` added call sites; the plan
   predicted 21 and 21 was measured, before editing. One call site (`:144-148`) shrank from a
   three-line call to one line and lost its now-pointless `target`/`mkdir` setup lines. The
   stub's signature was updated in the same commit.
3. **`KittySession.send_key`**: no caller in `src`, `tests` or `tools`. The only mention outside
   its definition was `tests/integration/test_h02_clear.py:15`, a docstring explaining the test
   does **not** use it. **This corrects the research's triage**, which filed `send_key` as
   test-used: the "use" was a docstring, not a call. The docstring sentence was reworded to name
   kitty's `send-key` verb instead of the deleted wrapper; the rationale (raw key events do not
   traverse the keymap) stays. Eight repro documents under `docs/repro/` (`h09`, `h11`–`h16`)
   record the same limitation independently. The module docstring's API list no longer
   advertises `send_key()`.
4. **`_find_tab_with_window`** (`tests/integration/test_h25_scene_launcher.py`): defined, never
   called; its sibling `_find_window_by_id` is used and survives.

**Kept, deliberately**: the `session_dir` property (dead at `bbed580`, read by `02-11`'s
`tests/unit/test_kitty_session_socket.py:60` and `:84` since — test-consumed, not dead), the
`ls`/`send_text`/`launch`/`get_text` wrappers, `uninstall_config_only`, `_find_window_by_id`,
`02-11`'s `_make_socket_dir`/`_remove_socket_dir` and socket-length check, `completer` ×4,
`exc_type`/`tb`, `pytest_collection_modifyitems`, `CompletionShell.BASH`, and the three pytest
fixtures (`fake_home`, `uninstall_stubs`, `isolated_completion_dir`). The eight allowlist
findings under five names and the three fixtures are `02-10`'s to resolve by configuration.

### Vulture arithmetic, checked against the real runs

- `uv run vulture src`: 15 before (the plan's 16 minus `reason`, already consumed by `02-07`)
  → **13** after, minus `env_path` and `send_key`, exactly the plan's predicted 13. The gate's
  ceiling of 13 is met with equality, and the negative half (no `reason`, `env_path` or
  `send_key` finding) passes.
- `uv run vulture --ignore-decorators '@pytest.fixture' src tests`: **12 → 8** — the plan's
  exact arithmetic. The 8 are `completer` ×4, `exc_type`, `tb`, `pytest_collection_modifyitems`,
  `BASH`; every non-blank output line matches the five allowlist names and nothing else
  (handover gate exit 0). No count ceiling on this gate, per the plan.
- `uv run vulture src tests`: 15 → **11** (the four dead findings leave).

### The experiment: whole integration suite after the deletions

`make test-integration PYTEST_ARGS='-q'` (`02-11`'s headless runner, nested `cage`,
`WLR_BACKENDS=headless`), wrapped in the plan's sampler gate:

- **78 passed** in 46.52s, zero failed, zero errors; make exited 0 (pytest exit status 0 read
  from the child's status file; compositor exited 0).
- The sampler observed **72 distinct harness-owned kitty PIDs** during the run (matched by
  `WLR_BACKENDS=headless` in `/proc/<pid>/environ`) and **none** afterwards; no `cage` process
  outlived the run.
- Transcript: `tmp/r011-sizing/integration-after.txt`. This is the experiment behind the two
  harness/integration-tree deletions, which `make test` cannot see; the commit waits on it and
  it is green.

## Spine gates

- `uv run make test` → **475 passed, 78 skipped**, zero failures (≥ 314 required). Includes the
  21 updated `env_path` call sites and the updated stub.
- `make doctor` → exit 0, all nine lines PASS/SKIP, no FAIL:
  `PASS kitty binary`, `PASS symlink`, `PASS desktop entry`, `PASS config payload`,
  `PASS sentinel block`, `PASS parse check`, `PASS bindings`, `PASS completion`,
  `SKIP remote-control` (no running kitty). The installed binary predates nothing this plan
  changed in behaviour — no `make install` was needed or run.
- Repo-wide deltas vs `1e9209a`: black 1 file → 0; ruff 6 → 2; pyright 14 → 6;
  bandit 33 → 33 (no growth); vulture 15 → 13 (`src`). All five counts shrank or held; none grew.

## The three red-until-`02-10` gates, recorded as red

1. **Whole-`src` ruff** (`uv run ruff check src`): exits 1 on the two S607. The four-shape half
   (no RUF001/E501/SIM105/RUF100) passes — the recorded output shows only S607. `02-10` makes
   the design call (absolutise the binaries or configure ruff with rationale).
2. **Whole-`src` pyright** (`uv run pyright src`): exits 1 on 6 errors — 5
   `reportPrivateUsage` (Phase 5 / R3.3 territory, `02-10` must not preempt) and 1
   `reportUnnecessaryComparison` (`kitty_session.py:210`, the latent bug the plan routes to
   `02-10`). `reportUnusedImport` is 0: the half this plan owns is done.
3. **No suppression comment in `src/`**: **15 lines** still carry one (measured after this
   plan's edits: eleven `# noqa` — ten `S603`, one `S310`, one `S108` is among them; exact list:
   `# noqa` ×11 at `_client.py:121`, `installer.py:150`, `installer.py:162` [S310],
   `installer.py:169`, `kitty_session.py:262` [S108], `kitty_session.py:265`,
   `kitty_session.py:307`, `doctor.py:47`, `doctor.py:144`, `config_updater.py:226`,
   `binding_introspection.py:155` — plus 4× `# type: ignore[attr-defined]` on `cli.py`'s
   `completer` assignments at `:214`, `:267`, `:402`, `:431`). The twelfth `# noqa` (the F401 in
   `scenes/__init__.py`) was **removed by this plan**. The plan's `fails_when` estimated 17 at
   `bbed580`; at `1e9209a` twelve `# noqa` + four `type: ignore` = 16 existed, and this plan took
   one away. Every survivor goes through a rationale-bearing config entry in `02-10`; this plan
   added none.

## Commit

| Kind | SHA | Subject |
|------|-----|---------|
| execute | (this commit) | `chore(02-09): the mechanical half of R0.11 — canonical formatting, declared re-exports, four dead symbols deleted (R0.11)` |

Staged by explicit path: the five `src/` files, the four test files, and this SUMMARY. The
`tmp/r011-sizing/` directory is gitignored and is carried into this SUMMARY by quotation and
table, per the step-0 rule.
