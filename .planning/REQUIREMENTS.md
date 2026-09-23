# Requirements: kitty-setup

**Defined:** 2026-09-22
**Source:** `docs/prds/kitty-setup-remediation-v1.0-prd.md` (v1.0, precedence override 0 via
`docs/prds/ingest-manifest.yaml`) — the PRD's own numbering (R0.1–R7.3) is preserved verbatim as
the requirement IDs.
**Core Value:** One trustworthy kitty setup that feels native on both Linux and macOS, where
`my-kitty doctor` is green and everything `my-kitty keys` prints is exactly what kitty actually
does in a live session.

## v1 Requirements

Requirements for this remediation milestone. Each maps to exactly one roadmap phase.

### R0 — Governance

> Note (2026-09-22, D-14): every "`CLAUDE.md`" below means the canonical instruction file,
> which R0.8 establishes as `AGENTS.md` (with `CLAUDE.md` reduced to an `@AGENTS.md` import).

- [ ] **R0.1**: `CLAUDE.md` carries a non-negotiable rule — *"Research, then experiment, then
      decide, then implement."* Any removal or replacement of behaviour (config line, chord, code
      path) requires (a) documented research (kitty docs/source/introspection) and (b) an
      experiment on a real kitty session with recorded evidence, **before** the decision.
- [ ] **R0.2**: `openspec/changes/phase1-curated-bindings-revert-defaults` is retired with
      `openspec archive --skip-specs` — the delta is NOT fixed and the main specs are NOT synced
      (reworded 2026-09-22, phase-1 discussion D-01/D-03: `openspec validate --strict` reports 7
      errors that will never be fixed because rewriting frozen specs is out of scope). The whole
      tree then moves to `.planning/legacy/openspec/` (D-02), and FROZEN banners land on
      `.planning/legacy/openspec/README.md`, `docs/requirements.md`, and
      `docs/propossal_roadmap.md` — each reading "FROZEN — history only; source of truth is
      `.planning/`".
- [ ] **R0.3**: `CLAUDE.md` and its authoritative-sources list point to `.planning/`; OpenSpec
      process references are retired (the hypothesis playbook `docs/agent-iteration.md` stays).
- [ ] **R0.4**: Git policy written into `CLAUDE.md` (replacing "No auto-commit"), reworded
      2026-09-22 per phase-1 discussion D-06: each phase runs in its own git worktree on branch
      `gsd/phase-{phase}-{slug}`; agents commit per plan (see R0.10), and at phase end — once `make doctor`
      and `make test` are green — merge into `master` and push. Agents MUST NOT force-push or
      amend pushed commits. A pre-push hook under `tools/hooks/`, wired via `core.hooksPath`,
      enforces this structurally rather than by acknowledgment (D-07/D-08).
- [ ] **R0.5**: `CLAUDE.md` carries a research-tooling rule (D-12): prefer `codegraph_explore` /
      `codegraph explore` before opening files; when a file must be read directly, size it first
      (`wc -l`, `rg -n '<symbol>'`) and read only the relevant range; prefer `rg`, `fd`, `wc`,
      `bat`, `sd`, `eza` over slower or more verbose equivalents.
- [ ] **R0.6**: The CodeGraph index lifecycle is automated (D-13): a newly created phase worktree
      gets an index built automatically (`.codegraph/` is gitignored, so a fresh worktree has
      none), and every commit refreshes it (`codegraph sync` preferred over a full rebuild). A
      CodeGraph failure warns and never aborts the commit or the worktree creation.
- [ ] **R0.7**: Every new GSD plan carries `cross_ai: true` in its frontmatter (D-10), so
      cross-AI execution is the default rather than per-plan opt-in.
- [ ] **R0.8**: `AGENTS.md` is the canonical instruction file and carries every agent rule
      (D-14): GSD's `project-instruction-file` resolves to `AGENTS.md`, and codex/opencode read it
      by convention, so rules kept only in `CLAUDE.md` would be invisible to the CLIs that execute
      plans. `CLAUDE.md` is reduced to the single line `@AGENTS.md`, and
      `.planning/config.json`'s `claude_md_path` is repointed.
- [ ] **R0.9**: A placement rule is written into `AGENTS.md` (D-15): rules and process live in
      `AGENTS.md` (validated with `agent-md-refactor`), project information for humans lives in
      `README.md` (validated with `crafting-effective-readmes`), and stack/tooling conventions stay
      in `.claude/conventions.md`. A rule belongs in exactly one file and is moved, never copied.
- [ ] **R0.10**: A commit-granularity rule is written into `AGENTS.md` (added 2026-09-22 at the
      user's request): **one commit per plan**, not one per task. An executor squashes a plan's
      work into a single logical commit whose message names the plan and the requirements it
      satisfies. A plan is split into more than one commit only when the changes are genuinely
      independent (e.g. an unrelated drive-by fix), and the reason is stated in the second
      commit's message. This supersedes "agents commit per task" in R0.4 — R0.4 keeps the worktree,
      merge, push and no-force-push half of the policy.

      **Amended 2026-09-23 by user direction: TDD is kept as commit topology.** A plan whose
      frontmatter is `type: tdd` produces **exactly two** commits — a RED commit containing only the
      new tests, subject `test(<phase>-<plan>): …`, at which those tests **fail**; then a GREEN commit
      with the implementation and the SUMMARY, subject `feat(<phase>-<plan>): …`. Every other plan
      still produces exactly one commit. The rule is two **per plan**, never per task: review round 1
      removed per-task RED/GREEN commits and that removal stands, because per-task was unbounded while
      a per-plan pair is a fixed shape a gate can assert — including RED-before-GREEN ancestry via
      `git merge-base --is-ancestor`.

      **This requirement and `workflow.tdd_mode` must move together.** With `tdd_mode: true`, GSD's
      harness gate demands a RED commit touching `tests/` before the implementation step of any task
      where `query task.is-behavior-adding` is true, matched at commit scope
      `^[a-z]+\((0*N)-(0*M)\):`. Measured: plans `01-01` and `01-02` are `type: tdd` and return
      `is_behavior_adding: true`. A one-commit-per-plan rule therefore makes that gate unsatisfiable —
      which is what the first version of this amendment resolved in the opposite direction (by turning
      `tdd_mode` off) before the user corrected it. Whichever way it is set, setting one without the
      other halts a phase mid-run or forbids a commit the gate requires.

- [ ] **R0.11**: **`src/` is clean under all five quality tools** — ruff, black, pyright, bandit,
      vulture (added 2026-09-23 at the user's direction after the gate's claim was measured and
      found false). Owned by **Phase 2**, the earliest phase that already edits these files.
      Measured baseline at `5452f54`: `src/` carries **19** of pyright's 571 errors; ruff's 28 and
      black's 11 files span `src`+`tests`+`tools`; bandit reports **0 high** (8 medium, 19 low —
      an earlier report of "20 high" misread bandit's *confidence* column as severity). From the
      moment this lands, "src clean" is a hard gate in the Universal Phase Gate step 5.
- [ ] **R0.12**: **`tests/` type-checks and lints clean**, so a real defect in a test is visible
      rather than buried in ~580 pre-existing findings. Owned by **Phase 8.5**. 96% of the debt is
      `typeCheckingMode = "strict"` applied to pytest bodies (`reportUnknownVariableType`,
      `reportUnknownArgumentType`, `reportUnknownLambdaType` dominate), which is noisy by nature
      and not evidence of broken tests — so a **deliberate, justified narrowing** of pyright's
      scope or mode for `tests` satisfies this requirement as fully as driving the count to zero.
      A silent scope reduction does not. No test's behaviour may change to satisfy a type checker:
      the suite's pass/fail set must be identical before and after, evidenced by both runs.

### R1 — Defect remediation

Each defect is a requirement with a regression test.

- [ ] **R1.1**: `my-kitty doctor`'s shell-completion check passes on a uv-tool install. Mechanism
      decided 2026-09-22 (phase-2 discussion D-01): install generates a **static completion file**
      (`register-python-argcomplete --shell bash|zsh my-kitty`) under
      `~/.local/share/kitty-setup/` and the rc block sources it, so no runtime PATH lookup is
      needed; doctor checks the generated file plus the rc source line. Root cause confirmed: the
      helper exists inside the uv tool venv but `uv tool install` exposes only `my-kitty`.
      **R1.1 unblocks Phase 1's merge.** `make doctor` was measured red on 2026-09-23 (exit 2, one
      FAIL: `register-python-argcomplete not on PATH`) — that failure *is* this requirement. Rather
      than write an expiring exemption so Phase 1 could merge against a red doctor, Phase 1 commits
      and pushes its branch and **defers its merge** until this requirement makes doctor green
      (user direction, 2026-09-23). Two consequences:
        - No `PHASE-1-DOCTOR-CARVE-OUT` marker is ever written. The check
          `for F in AGENTS.md .planning/ROADMAP.md .planning/PROJECT.md; do if rg -q 'PHASE-1-DOCTOR-CARVE-OUT' "$F"; then exit 1; fi; done`
          must hold at every point, not merely become true later — it guards against the exemption
          being reintroduced, which is stricter than the round-2 (O2) form it replaces.
        - `gsd/phase-1-governance-freeze` merges to `master` only once `make doctor` exits 0 with
          every check PASS or SKIP. R1.1 is therefore a release gate for two phases, not one.
- [ ] **R1.2**: `make clean` behaviour and help text agree; `clean` MUST NOT delete `kitty.app` or
      backups.
- [ ] **R1.3**: `tools/uninstall.sh` logs to stderr inside `resolve_binary`; the legacy-binary
      branch works; errors are visible.
- [ ] **R1.4**: Scene fill-current-tab shell-quotes pane-0 `cwd` (`shlex.quote`), and pane-0 `cmd`
      honours the same `bash -lc` semantics as every other pane.
- [ ] **R1.5**: Config parse check reports the actual command used, surfaces parser stderr on
      failure, and rolls back the payload dir on failure; the doctor label is fixed.
- [ ] **R1.6**: Integration tests strip `KITTY_WINDOW_ID` (h25, `scene_recipe_e2e`) so results do
      not depend on being run inside kitty.
- [ ] **R1.7**: Minor defects: the install log is **removed** entirely (reworded 2026-09-22,
      phase-2 discussion D-11 — nothing reads it and the spec that required it is frozen history;
      it was previously specified as "relocate outside the uv venv"); guard `int(stdout)` in the
      launcher → clean error; an empty/whitespace color is treated as **absent** (no kitten
      argument emitted, matching the recipe loader's convention) and passthrough is narrowed to
      **`rgb:` only** (reworded 2026-09-23 from "real `rgb:`/`rgba:`/functional forms" — measured
      against kitty 0.49.0's own parser, which accepts `rgb:ff/00/00` and rejects `rgba:ff/00/00/80`,
      `rgb(1,2,3)`, `rgba(1,2,3,0.5)` and `hsl(1,2%,3%)`, so the wider list named forms kitty cannot
      consume; U-2 in `.planning/phases/02-defect-remediation/02-RESEARCH.md`); `prune --keep <0` →
      argparse error; **the harness teardown verb stays `close-window`** (reworded 2026-09-23: the
      original "teardown `close-os-window`" is not implementable — `close-os-window` is not a
      `kitten @` subcommand in kitty 0.49.0, only a mappable action, and the teardown call is wrapped
      in `except HarnessCommandError: pass`, so implementing it literally would leak one kitty process
      per integration test **silently**; `close-window` was measured correct with 2 OS windows and 3
      windows; U-1 in 02-RESEARCH.md); doctor "skipped" → real SKIP state; PATH-migration messages
      printed as specified; unsupported-shell hint prints both lines.
- [ ] **R1.8**: Introspection macOS attribution — normalise payload chords through kitty's own
      `parse_shortcut` (in the same `+runpy` call) so `cmd+k` ≡ `super+k` attributes to our file
      (mechanism decided 2026-09-22, phase-3 discussion D-06; both verified to parse to
      `mods=8, key_name='k'`). Owned by Phase 3, not Phase 2.

### R2 — Cross-OS keybinding harmonization

- [ ] **R2.1**: Model is **native per-OS**: kitty's own defaults are authoritative on each OS
      (ctrl+shift on Linux; cmd on macOS where kitty defines cmd chords). Add or override a chord
      only for (a) a new action, (b) a behaviour change (cwd inheritance, instant clear), or (c) a
      conflict with a chord our helper owns. Every such line is justified in the allow-list.
- [ ] **R2.2**: Research deliverable — a chord matrix `docs/research/kitty-default-chords.md` for
      kitty ≥0.49 (Linux vs macOS), sourced from kitty docs/source + `kitty +runpy` introspection,
      plus a list of every current payload line classified as new / behaviour-override / redundant
      restatement.
- [ ] **R2.3**: cwd inheritance applies to both OSes' chords: Linux `ctrl+shift+t/n/enter`; macOS
      `cmd+t`, `cmd+n`, `cmd+enter` (plus the ctrl+shift variants kitty binds there).
- [ ] **R2.4**: Instant clear — `super+k` (Linux), `cmd+k` (macOS, a **declared override** of
      kitty's `clear_terminal to_cursor`), `ctrl+shift+alt+k` fallback on both. Wipes screen +
      scrollback.
- [ ] **R2.5**: Redundant restatement lines (tab-nav, window-nav, font-zoom, url-hints) are
      removed **only if an experiment proves** `my-kitty keys` can categorise kitty defaults in
      code (action→category table) with identical grouping output, verified on Bazzite and macOS.
      Otherwise they stay and the reason is documented.
- [ ] **R2.6**: `my-kitty keys` reports 0 conflicts on both OSes; the per-OS chord set is
      documented.
- [ ] **R2.7**: Custom chords (`ctrl+shift+m`, `ctrl+shift+i`, `ctrl+shift+d`,
      `ctrl+shift+alt+d`, `ctrl+shift+alt+c`, scene chords) verified free on BOTH OSes' default
      maps.
- [ ] **R2.8**: **`my-kitty keys` is truthful** (primary goal, not a side effect of cleanup):
      (a) **effective** — the chord→action shown is what kitty resolves at runtime after all
      includes/overrides; no shadowed or dead line shown as active, shadowed ones shown only as
      "shadowed by …";
      (b) **correct attribution** — source file/category is the real origin (payload file vs kitty
      default vs user `kitty.conf`), chords normalised by kitty's own parser;
      (c) **OS-correct** — the default set is the host OS's (macOS cmd chords appear on macOS
      only, never a Linux list reused on macOS);
      (d) **no phantoms/duplicates/stale entries** — no entry for a chord kitty does not bind, no
      double-listing, no action text differing from kitty's current wording (e.g. `… smooth`);
      (e) **user overrides visible** — bindings from the user's own `kitty.conf` outside our block
      are listed and flagged if they shadow ours.
      **Oracle test**: an integration test starts a real kitty session (harness) with the
      installed config, obtains kitty's effective keymap **independently of
      `binding_introspection`** (kitty's own runtime/debug-config output), and asserts
      `my-kitty keys --json` equals it **1:1 on chord, action, and source**. It runs on Linux in
      every phase that touches bindings and on macOS in R7. It is the acceptance gate for R2 and
      R5.3.

### R3 — Foundation/scenes separation + doctor minimum version

- [ ] **R3.1**: Foundation and scenes are installable/uninstallable independently
      (`my-kitty install/uninstall --component foundation|scenes|all`, default `all`);
      `install --no-config` does not seed scenes unless the scenes component is selected (today
      `seed_scenes()` runs unconditionally at `installer.py:229` — a live bug). Mechanism decided
      2026-09-22 (phase-5 discussion D-01): the payload splits into `foundation/` and `scenes/`
      **subdirectories**, each with its own entry file, included from the payload-root
      `kitty-setup.conf`. `--component` and the existing `--keep-*` flags are **orthogonal** axes,
      and a `--keep-*` that cannot apply to the selected component is a no-op the output states
      explicitly (D-06). A scenes uninstall **never deletes user data**: only the payload subdir and
      seeded examples still byte-identical to what we shipped are removed (D-07).
- [ ] **R3.2**: Scenes keep working after a foundation uninstall, because `remote-control.conf` and
      `dynamic-opacity.conf` are **scenes-owned** (decided 2026-09-22, phase-5 discussion D-02 —
      both files' own headers already declare the dependency, so no new error path is needed). The
      honest converse: a foundation-only install has no remote control, and `doctor`'s
      remote-control check must report that as a SKIP naming the scenes component rather than
      telling the user to run `make install`.
- [ ] **R3.3**: Cross-imports removed (`doctor.py:18`→`scenes._client`,
      `installer.py:98`→`scenes.recipe`, `scenes/_client.py:18`→`config_updater`/`installer`) via
      shared neutral module(s) — recommended split: path resolution and socket discovery, separated
      by reason to change (D-12). Enforcement decided 2026-09-22 (phase-5 discussion D-11): a
      **pytest test walking the AST of `src/`**, which catches deferred in-function imports (the
      form `installer.py:98` uses to dodge a load-time cycle) and also asserts the neutral module
      imports neither side. It gates both `make test` and the `tools/hooks/` pre-commit hook. Ruff
      cannot express the rule — its `banned-api` is global and `per-file-ignores` filters by rule
      code, not by banned name.
- [ ] **R3.4**: Doctor enforces a minimum supported kitty version — the constant is **0.49**
      (decided 2026-09-22, phase-5 discussion D-09: the only version the oracle, chord matrix and
      payload were verified against; 0.46 is provably wrong on action text since `scroll_line_*`
      became `smooth` in ≥0.47). FAIL below it with an upgrade hint, PASS at or above it, and FAIL
      explicitly when the version string cannot be parsed. Detection parses the `kitty --version`
      string `_check_kitty_binary` already captures rather than adding a `+runpy` round trip (D-10).
- [ ] **R3.5**: The payload walk is **recursive** (`binding_introspection.py:183` `glob`→`rglob`),
      so `my-kitty keys` still attributes every payload binding to its own file after the R3.1 move
      (added 2026-09-22, phase-5 discussion D-03). Non-negotiably in the same plan as the move: the
      non-recursive glob would silently report 0 ours / 101 defaults and 0 conflicts — vacuously
      true, and exactly the R2.8 class. The Phase 3 oracle must be green after it.

### R4 — Pane color cycle

- [ ] **R4.1**: `ctrl+shift+alt+c` (both OSes) rotates the **focused pane's background AND its tab
      accent** through the palette, using exactly the existing behaviours of
      `my-kitty window background <color>` and `my-kitty tab accent <color>` (no color
      transformation). The chord **always sets both**, last-write-wins when a tab holds several
      panes (decided 2026-09-22, phase-6 discussion D-04): `set-tab-color` is tab-scoped in kitty,
      so some pane must win, and a solo-tab guard would make one chord behave two ways depending on
      pane count.
- [ ] **R4.2**: Default palette = existing color names, in order: `blue, green, red, yellow,
      purple, teal, orange, gray, none` (`none` resets both). Stored in an editable user file —
      decided 2026-09-22 (phase-6 D-05): **TOML** at `$XDG_CONFIG_HOME/kitty-setup/palette.toml`,
      beside `scenes/` and seeded copy-if-absent via `seed_scenes()`'s existing contract, so a
      user-edited palette is never overwritten. TOML was chosen for alignment with R5.1's preset
      TOML — one format, one loader. Entries validate through `normalize_color` **at load time**,
      with an error naming file/entry/line; a missing or empty palette falls back to the built-in
      default order, because the chord has nowhere to show a parse error (D-06). All nine entries
      were verified to resolve already.
- [ ] **R4.3**: Stateless — the next color is derived from the pane's current background
      (`kitten @ get-colors --match`), and any background not matching a palette entry advances to
      the **first** entry, so a reset pane and a never-cycled pane behave identically (phase-6 D-01).
      Additionally (D-02): if the user's *configured* default background equals a palette entry's
      hex, that entry is unreachable and the cycle would silently skip it — detect that collision and
      surface it rather than misbehaving quietly. Matching compares `normalize_color`-normalised
      values, and the exact `get-colors` output format is pinned by experiment before the comparison
      is written (D-03).
- [ ] **R4.4**: New CLI `my-kitty window cycle-color [--reverse] [--match] [--to]`; the chord is a
      **`launch --type=background`** map line invoking that CLI (decided 2026-09-22, phase-6 D-07 —
      the only option where chord and shell share one code path, which is what makes the criterion
      testable; `remote_control_script` was rejected as a second implementation inside kitty's
      runtime). Open item for the experiment (D-08): whether `KITTY_WINDOW_ID` and socket resolution
      reach a `--type=background` launch, with `--match id:@active-kitty-window-id` as the fallback.
      The chord's `map` line lands under the payload's `scenes/` subdir (Phase 5 D-01/D-02), since it
      depends on remote control. Latency target ≤300 ms per press on Linux — measured non-binding
      (`kitten` spawns in ~10 ms, `my-kitty` starts in ~45 ms), so it is asserted, not designed around.

### R5 — Presets + chord→scene

- [ ] **R5.1**: Window presets (title+emoji, bg, accent, optional cmd) and tab presets (title,
      accent, layout) are defined once by name in user TOML; scenes reference presets by name and
      may override individual fields.
- [ ] **R5.2**: Backward compatible with existing inline scene recipes and the seeded examples.
- [ ] **R5.3**: Chord→scene — a user-declared mapping (scene name → chord) rendered into the
      payload; chords validated free on both OSes; `my-kitty keys` shows them under `scenes`.

### R6 — Live-doc hygiene

> The PRD states R6 as one unnumbered paragraph. It is split here into two checkable items
> (R6.1, R6.2) without adding scope; the "frozen OpenSpec is not rewritten" clause is recorded
> under Out of Scope rather than as a requirement.

- [ ] **R6.1**: CLI help text, docstrings, README, scene example headers, and the `CLAUDE.md`
      "Stack" section match actual behaviour.
- [ ] **R6.2**: Every changed behaviour has a repro doc with both a Linux status section and a
      macOS status section.
- [ ] **R6.3**: **`.claude/conventions.md` and the `Makefile` agree on which targets exist**
      (added 2026-09-23; surfaced by the Phase 1 replan as genuinely unowned, distinct from the
      quality-tool gap R0.11/R0.12 now own). `.claude/conventions.md:60-69` requires
      `make validate`, `make format`, `make test-unit` and `make test-integration`, and says
      "Never commit code that fails `make validate`" — **none of those four targets exist in the
      `Makefile`**. Resolve in whichever direction is true: add the targets (subject to the
      five-line-per-target stack rule) or rewrite the conventions text to name the commands that
      really work. A convention nobody can run is worse than no convention, because it reads as
      satisfied.

### R7 — macOS end-to-end verification and remediation over SSH

- [ ] **R7.1**: Separate phase + plan. Prerequisites the user performs once, documented in the
      plan: enable Remote Login on the Mac, add this host's SSH key, install uv + git, clone the
      repo, log into the GUI session (kitty needs it), share the host alias.
- [ ] **R7.2**: Agents drive e2e from Bazzite over SSH within the same session: `make install`,
      `my-kitty doctor`, `my-kitty keys`, launch kitty in the Mac GUI session (`open -a kitty` /
      `launchctl asuser`), drive it via `kitten @` over its unix socket, run the integration
      suite, and record evidence into the repro docs' macOS sections.
- [ ] **R7.3**: Anything not automatable (physical keypress feel) becomes a short manual UAT
      checklist.
- [ ] **R7.4**: This phase **fixes** what it finds, it does not only report. Any macOS-specific
      defect surfaced by the run — chord attribution, the `cmd+k` override, doctor checks, per-OS
      config selection, the installer's macOS path — is remediated inside this phase under the
      same Universal Phase Gate (research → experiment on the Mac → decide → implement → green
      gates), with the macOS oracle test (R2.8) as the acceptance check. Defects that are not
      macOS-specific are recorded and routed to the phase that owns them instead of being fixed
      here.
- [ ] **R7.5**: An SSH runbook (`docs/ssh-macos-runbook.md`) makes the Mac reachable without the
      driving session losing context: key-based Remote Login setup, a persistent/multiplexed
      connection (`ControlMaster`/`ControlPersist`) so repeated commands do not re-authenticate,
      and kitty's remote-control **unix socket forwarded** to the Linux host
      (`ssh -L /tmp/kitty-mac.sock:/tmp/kitty-<pid> <host>`, OpenSSH ≥6.7 supports unix-socket
      forwarding) so `kitten @ --to unix:/tmp/kitty-mac.sock` drives the Mac's kitty from Bazzite.
      The runbook states which steps are the human's and which the agent's; the forwarding
      mechanism is verified by experiment before it is relied on, per the mantra.
- [ ] **R7.6**: This is the milestone's one **human-in-the-loop** phase: it cannot run unattended
      because the Mac needs a logged-in GUI session and the one-time prerequisites. The phase plan
      states that explicitly, and the roadmap flags it so an autonomous run stops here rather than
      failing obscurely.

### R8 — Distribution (added 2026-09-22)

- [ ] **R8.1**: `tools/install.sh` installs kitty-setup end-to-end on a clean host via
      `curl -fsSL <raw-url> | bash`, with no prior repo clone, and its trust model is documented
      the way `../wezterm-setup/docs/install.md` documents its own.
- [ ] **R8.2**: The installer accepts a channel selection (rolling vs pinned release) and installs
      the selected channel; the default is stated explicitly in `--help` and in the README.
- [ ] **R8.3**: After a `curl | bash` install, `my-kitty uninstall` still leaves no trace —
      verified on a host that never had the repo — and the macOS path is exercised over the
      Phase 10 SSH harness with recorded evidence (the Mac-side run is owned by Phase 10).
- [ ] **R8.4**: Phase 9 **builds** the macOS distribution path, it does not defer it: the
      installer detects the host OS and selects the macOS install steps (kitty.app placement, PATH
      edit for the host shell, per-OS `clear.conf` variant), and the channel selection works
      identically on both OSes. Phase 9 verifies what it can on Linux and marks the macOS path a
      documented hypothesis; Phase 10 runs it on a real Mac and fixes it under R7.4.

## Cross-Cutting Gates

These are not phase-scoped requirements; they apply to **every** phase and are verified before a
phase can be called done. Sourced from the PRD's "Quality Standards" and "Constraints".

- **Process gate**: research → experiment (real kitty session, recorded evidence in
  `tmp/h<NN>-<slug>/`) → decide → implement → verify (R0.1, `docs/agent-iteration.md`).
- **Green gate**: `make doctor` and `make test` output captured as evidence. No "should work".
- **Code quality**: ruff, black, pyright, bandit, vulture clean (`.claude/conventions.md`).
- **Test coverage**: each requirement has unit and/or integration tests; integration gated by
  `KITTI_INTEGRATION=1` and green.
- **Performance**: instant clear ≤200 ms; color cycle ≤300 ms — measured in integration tests.
- **Security**: no new world-readable sockets; remote-control socket stays user-scoped; SSH
  key-auth only.
- **Binding gate**: any phase that touches bindings re-runs the R2.8 oracle test on Linux
  (Phases 3, 4, 7; macOS in Phase 10).
- **Git gate**: each phase runs in its own git worktree on branch `gsd/phase-{phase}-{slug}`; work
  lands at the granularity `AGENTS.md`'s commit-granularity rule states — that bullet is the only
  place in the repo where the rule is written, so it is pointed at rather than repeated here; at
  phase end, once `make doctor` and `make test` are green, merge into `master` and push; never
  force-push or amend pushed commits (R0.4 as reworded per D-06, with its granularity half
  reworded per D-16). Structurally enforced by `tools/hooks/pre-push`, whose every limit is
  disclosed in `AGENTS.md`'s git-policy bullet and in the hook's own header.

## Edge Cases To Cover

From the PRD's "Edge Cases". Each belongs to the phase that owns the relevant behaviour.

| Edge case | Owning phase |
|-----------|--------------|
| Multiple kitty instances (socket disambiguation) | Phase 6 |
| Pane with a custom background not in the palette | Phase 6 |
| `none` resets both background and tab accent | Phase 6 |
| Compositor grabbing `super+k` (fallback `ctrl+shift+alt+k`) | Phase 4 |
| kitty versions below the minimum | Phase 5 |
| Paths containing spaces | Phase 2 |
| Running tests from inside kitty | Phase 2 |
| Mac unreachable → Phase 10 blocked, all other phases unaffected | Phase 10 |

## v2 Requirements

Acknowledged but deferred; not in this roadmap.

### Deferred

- **Kitten promotion** — promote helper behaviour into a real kitty kitten.
- **Suspend/resume survival hardening** — beyond the existing behaviour.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Suspend/resume survival work | Existing behaviour stays as-is; unbounded investigation, not blocking daily use |
| kitty auto-upgrade on reinstall | Upgrading kitty stays the user's action; doctor only reports a too-old version (R3.4) |
| Kitten promotion | Deferred; the CLI + `kitten @` remote control covers everything in scope here |
| Rewriting frozen OpenSpec specs | `openspec/` is history-only after R0.2; correcting stale specs has no payoff now that `.planning/` is authoritative |
| Merging to `master` outside a green phase boundary | Merging **at** a green phase boundary is in scope per D-06: the phase-end flow merges into `master` and pushes once `make doctor` and `make test` are green. What stays out of scope is any merge, force-push or amend of pushed commits outside that boundary — `tools/hooks/pre-push` rejects it (R0.4 as reworded) |

## Traceability

Every v1 requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| R0.1 | Phase 1 | Pending |
| R0.2 | Phase 1 | Pending |
| R0.3 | Phase 1 | Pending |
| R0.4 | Phase 1 | Pending |
| R0.5 | Phase 1 | Pending |
| R0.6 | Phase 1 | Pending |
| R0.7 | Phase 1 | Pending |
| R0.8 | Phase 1 | Pending |
| R0.9 | Phase 1 | Pending |
| R0.10 | Phase 1 | Pending |
| R0.11 | Phase 2 | Pending |
| R0.12 | Phase 8.5 | Pending |
| R1.1 | Phase 2 | Pending |
| R1.2 | Phase 2 | Pending |
| R1.3 | Phase 2 | Pending |
| R1.4 | Phase 2 | Pending |
| R1.5 | Phase 2 | Pending |
| R1.6 | Phase 2 | Pending |
| R1.7 | Phase 2 | Pending |
| R1.8 | Phase 3 | Pending |
| R2.2 | Phase 3 | Pending |
| R2.5 | Phase 3 | Pending |
| R2.8 | Phase 3 | Pending |
| R2.1 | Phase 4 | Pending |
| R2.3 | Phase 4 | Pending |
| R2.4 | Phase 4 | Pending |
| R2.6 | Phase 4 | Pending |
| R2.7 | Phase 4 | Pending |
| R3.1 | Phase 5 | Pending |
| R3.2 | Phase 5 | Pending |
| R3.3 | Phase 5 | Pending |
| R3.4 | Phase 5 | Pending |
| R3.5 | Phase 5 | Pending |
| R4.1 | Phase 6 | Pending |
| R4.2 | Phase 6 | Pending |
| R4.3 | Phase 6 | Pending |
| R4.4 | Phase 6 | Pending |
| R5.1 | Phase 7 | Pending |
| R5.2 | Phase 7 | Pending |
| R5.3 | Phase 7 | Pending |
| R6.1 | Phase 8 | Pending |
| R6.2 | Phase 8 | Pending |
| R6.3 | Phase 8 | Pending |
| R7.1 | Phase 10 | Pending |
| R7.2 | Phase 10 | Pending |
| R7.3 | Phase 10 | Pending |
| R7.4 | Phase 10 | Pending |
| R7.5 | Phase 10 | Pending |
| R7.6 | Phase 10 | Pending |
| R8.1 | Phase 9 | Pending |
| R8.2 | Phase 9 | Pending |
| R8.3 | Phase 10 | Pending |
| R8.4 | Phase 9 | Pending |

**Note on R1.8 and R2.8:** R1.8 (chord normalisation through kitty's parser) sits in Phase 3, not
Phase 2, because it is a prerequisite of the R2.8 oracle's attribution assertion. R2.8's oracle
test is *built* in Phase 3 and *re-run as a gate* in Phases 4, 7, and 9 — it is owned by Phase 3
and is not double-mapped.

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-22*
*Last updated: 2026-09-22 after initial ingest of `docs/prds/kitty-setup-remediation-v1.0-prd.md`*
