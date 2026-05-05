## 1. Probes (already done — see tmp/probes/phase1-binding-introspection/)

- [x] 1.1 Probe 01 — verified kitten/kitty has no built-in `list-keys` / `list-bindings` command. Verdict: fails. → forces D1 (`kitty +runpy` enumeration).
- [x] 1.2 Probe 02 — verified `kitty.config.load_config(...).keyboard_modes[""].keymap` exposes a `dict[SingleKey, list[KeyDefinition]]` we can walk. Verdict: holds. → enables D1.
- [x] 1.3 Probe 03 — verified `KeyDefinition.definition_location` is reset to empty post-parse and cannot attribute source file. Verdict: fails. → forces D2 (manual pre-walk of our payload files).
- [x] 1.4 Probe 04 — verified duplicate chords appear as multiple `KeyDefinition` in `defs[]`. Verdict: holds. → enables D3 (conflict detection). Bonus: discovered `ctrl+shift+-` regression already shipped, motivates this entire change.

## 2. Hypothesis H03 — wire enumeration end to end

- [ ] 2.1 Create `tmp/h03-introspection/repro.md` describing the manual repro (run `my-kitty keys`, expect grouped report with N ours / N defaults / N conflicts; expect ctrl+shift+- flagged as conflict, ctrl+shift+t flagged as override).
- [ ] 2.2 Create `tmp/h03-introspection/run.py` that: (a) writes a candidate `intentional-overrides.conf` to a scratch dir, (b) writes a small kitty.conf into the scratch dir that includes our windowing.conf + bindings.conf via absolute path, (c) drives the planned introspection module against that scratch config, (d) asserts the report shape: 4 windowing entries, 1 bindings entry, 4 overrides allow-listed, 1 real conflict on `ctrl+shift+-`.
- [ ] 2.3 Iterate the module's logic in `tmp/h03-introspection/draft.py` until `run.py` is green.

## 3. Promote `kitty-binding-introspection`

- [ ] 3.1 Move proven module logic to `src/kitty_setup/binding_introspection.py`. Public API: `enumerate(conf_path: Path, kitty_bin: Path, payload_dir: Path, allow_list: Path) -> Report`, plus `Report.render_text() -> str` and `Report.to_json() -> str`. The subcommand handler `cli_keys(args: argparse.Namespace) -> int` parses `--json` and `--config-path` and resolves the remaining parameters from defaults: `kitty_bin` via `shutil.which("kitty")` with fallback to `installer.SYMLINK_PATH` then `installer._kitty_bin(installer.DEFAULT_DEST)`; `payload_dir` from `config_updater.ConfigPaths.for_user().payload_dir`; `allow_list` from `payload_dir / "intentional-overrides.conf"`. If `kitty_bin` cannot be resolved, the handler prints a descriptive `FAIL` message and returns non-zero rather than raising.
- [ ] 3.2 Register `keys` as a subparser in `src/kitty_setup/cli.py`: `sub.add_parser("keys", help="list active key bindings + flag conflicts")` with `--json` and `--config-path` arguments, dispatched via `set_defaults(func=binding_introspection.cli_keys)`. Add `binding_introspection` to the existing `from kitty_setup import doctor, installer, pruner` line. NO `[project.scripts]` change — `keys` is a subcommand of the existing `my-kitty` binary.
- [ ] 3.3 Ship `config/kitty/intentional-overrides.conf` with the four bootstrap overrides (`ctrl+shift+t`, `ctrl+shift+n`, `ctrl+shift+enter`, `ctrl+shift+k`). The config_updater payload-mirror step already copies new files into `~/.config/kitty/kitty-setup/`; verify after `make install`.
- [ ] 3.4 Promote `tmp/h03-introspection/repro.md` to `docs/repro/h03-introspection.md`. Rewrite `tmp/h03-introspection/run.py` as `tests/integration/test_h03_introspection.py` using a pytest fixture for the scratch config and the `KITTI_INTEGRATION` gate. Delete `tmp/h03-introspection/`.
- [ ] 3.5 Add `tests/unit/test_binding_introspection.py` covering: pure parsing helpers (file regex, chord normalisation, conflict classification) against synthetic input. No real kitty in the unit test (per R7, the integration test in 3.4 is the real-system verifier; the unit test is a fast regression net for the pure-Python helpers).

## 4. Modify `kitty-install` (doctor)

- [ ] 4.1 Update `src/kitty_setup/doctor.py`: add a 7th check that invokes the introspection module (in-process, no subprocess fork-overhead per check) and emits `PASS|FAIL bindings: <N> ours, <N> defaults, <N> conflicts`. FAIL only when conflicts > 0. Error path: if the introspection module raises (e.g. `kitty_bin` not found, config file unreadable, `+runpy` returns non-zero), the check must catch the exception and return `CheckResult("bindings", False, "skipped — <reason>")` — matching the existing pattern used by `_check_parse()` — rather than propagating the exception and crashing `make doctor`.
- [ ] 4.2 Update `tests/unit/test_doctor.py` to cover the new check (mock the introspection module's `enumerate()` with synthetic Reports for both healthy and conflict-present cases). **Important:** the existing `test_run_checks_reports_each_check` assertion hardcodes the list `["kitty binary", "symlink", "desktop entry", "config payload", "sentinel block", "parse check"]` (6 names, line 70–77). That assertion must be updated to include `"bindings"` as a 7th name, or it will break the moment the new check is added to `run_checks()`.
- [ ] 4.3 Run `make doctor` on this Pop!_OS box. Expected: 6/7 PASS; new bindings check FAIL with `1 conflict` (the `ctrl+shift+-` regression). Capture the output verbatim into the eventual commit message — the regression is the proof the introspection works.

## 5. Documentation

- [ ] 5.1 Update `docs/agent-iteration.md`: add a one-line note in the loop step 6 (Promote) that any new file added under `config/kitty/` becomes a binding category by file basename. Cross-link to the new spec.
- [ ] 5.2 README: add `my-kitty keys` to the quickstart command list, with a one-line description ("list every active binding grouped by source file; flags conflicts with kitty defaults").

## 6. Probe-finding durability check (R6)

- [ ] 6.1 For each of probes 01–04, encode the finding into a durable location:
  - 01 finding ("no built-in list-keys") → `Why:` line on D1 in `design.md` (already in place).
  - 02 finding ("runpy + load_config exposes keymap") → inline comment at the `+runpy` invocation in `binding_introspection.py` referencing `probe-phase1-binding-introspection-02`.
  - 03 finding ("definition_location is reset post-parse") → inline comment at the manual file-walk in `binding_introspection.py` referencing `probe-phase1-binding-introspection-03`.
  - 04 finding ("conflicts = `len(defs) > 1` modulo allow-list") → inline comment on the conflict classifier referencing `probe-phase1-binding-introspection-04`.
- [ ] 6.2 Confirm `tmp/probes/` will disappear cleanly when this change archives (gitignored; no special action needed).

## 7. Final sweep

- [ ] 7.1 Run `make doctor`. Capture output; expect FAIL on the new bindings check (the `ctrl+shift+-` regression).
- [ ] 7.2 Run `KITTI_INTEGRATION=1 make test`. Capture output; expect all unit + integration tests green.
- [ ] 7.3 Run `openspec validate phase1-binding-introspection --strict`. Expect "Change is valid".
- [ ] 7.4 Two or three commits (introspection module + doctor wiring + tests, then docs, then tasks-changelog). `openspec archive phase1-binding-introspection -y` syncs the new + modified specs.
- [ ] 7.5 Open follow-up change `fix-ctrl-shift-minus-collision` to move the horizontal-split chord off `ctrl+shift+-` (e.g. to `ctrl+shift+s`). The introspection report from this change is its verification gate: doctor must return to 0 conflicts before that change archives.
