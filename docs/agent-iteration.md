# Agent Iteration Playbook

This is the operating manual for advancing kitty-setup one behavior at a time.
Read this before opening another OpenSpec change or picking the next item from
[docs/requirements.md](requirements.md). The rules here are not aspirational; they
are how the previous attempt did not fail again.

## Operating principles

### R1 — Investigate first

No code lands in `src/`, `config/`, or `tests/integration/` until a hypothesis run
in `tmp/h<NN>-<slug>/` is green against a real kitty session. The hypothesis directory
is the only place where speculative code is allowed to live.

### R2 — Verify before declaring done

A behavior is "ready" only when `make doctor` and `KITTI_INTEGRATION=1 make test`
both exit 0 and their output is captured into the change's PR description or handoff.
"Should work", "compiles", "looks right" are not evidence. The output of the verifying
command, with its exit code, is.

### R3 — Makefile is thin

Each Make target is at most five lines, including its banner. Anything longer is
extracted into `tools/<name>.sh` (bash, only allowed in bootstrap territory) or a
`[project.scripts]` entry point under `src/kitty_setup/`. The Makefile is glue, not
logic.

### R4 — Dogfood the bootstrap

The infrastructure (installer, config_updater, harness) is itself proven via
hypothesis runs (H00, H0a, H0b) before any user-facing behavior is built on top of it.
We do not assume our own scaffolding works.

### R5 — No promotion shortcut

`tmp/` is gitignored. Promotion is a manual rewrite, never a `cp` or a symlink.
Configuration migrates to `config/kitty/<topic>.conf`. The repro doc moves into
`docs/repro/h<NN>.md`. The autonomous probe is rewritten as a real
`tests/integration/test_h<NN>_*.py` using pytest fixtures and the `KITTI_INTEGRATION`
gate. The hypothesis directory is then deleted.

## The loop

For every Phase 1 item (after items 1 and 2, which are covered by the bootstrap
change), repeat:

1. **Pick the next item** from [docs/requirements.md](requirements.md), in the
   easy-to-hard order it documents. Skip an item only with a written reason in the
   OpenSpec proposal.

2. **Open an OpenSpec change** for the item. One change per Phase 1 item. Use
   `openspec new change <kebab-case-name>` and the `/opsx:propose` skill to scaffold
   `proposal.md`, `design.md`, the per-capability `specs/`, and `tasks.md`. Each item
   gets its own capability under `openspec/specs/` once the change is archived.

3. **Drop scratch** into `tmp/h<NN>-<slug>/`:
   - `repro.md` — what the behavior is, the manual repro steps, the expected
     observable outcome (cwd is `/tmp`, screen is empty, etc).
   - `run.py` — an autonomous probe using `kitty_setup.harness.KittySession` that
     drives a real kitty session and asserts the expected outcome.
   - `expected.json` — a structured form of the expected outcome (often the
     interesting subset of `kitty @ ls` output).
   - `actual.json` — captured by `run.py` on the latest run; gitignored.
   - `draft.conf` — the candidate kitty config snippet being iterated on.

4. **Iterate** the candidate `draft.conf` until `run.py` is green. Capture the green
   `actual.json` so the next agent can see what was observed.

5. **Promote** by hand:
   - Move the proven snippet into `config/kitty/<topic>.conf` (creating the file if
     needed). Update `config/kitty/kitty-setup.conf` to `include` it.
   - Move `repro.md` into `docs/repro/h<NN>-<slug>.md`.
   - Rewrite `run.py` as `tests/integration/test_h<NN>_<slug>.py` using pytest
     fixtures and the `KITTI_INTEGRATION` gate.
   - Delete the `tmp/h<NN>-<slug>/` directory.

6. **Verify** end-to-end: `make doctor` exits 0 and `KITTI_INTEGRATION=1 make test`
   exits 0. Capture both outputs into the change's eventual PR description.

7. **Archive** the OpenSpec change with `openspec archive <name>`. The capability
   spec moves from `openspec/changes/<name>/specs/` into `openspec/specs/`.

## Hand-off across agents

The agent that writes a hypothesis is *not* the same agent that promotes it. This
is the spec-first rule (CLAUDE.md) applied to the hypothesis layer. Concretely:

- The agent that authors `tmp/h<NN>-<slug>/run.py` and gets it green leaves the
  green `actual.json` and an updated `repro.md` describing what it observed.
- A separate agent reads the green hypothesis, decides whether the captured
  evidence justifies promotion, and performs the manual rewrite into `src/`,
  `config/`, `docs/repro/`, and `tests/integration/`.
- If the second agent disagrees with the hypothesis, it amends `repro.md` with
  the disagreement and the change goes back to step 4 with a new hypothesis.

## What to do when the harness disagrees with the manual repro

The autonomous probe is the source of truth. If the manual repro says a behavior
works and the autonomous probe says it does not, the behavior does not ship. Either
the probe is wrong (fix the probe) or the behavior is wrong (fix the config). The
manual repro is documentation; the probe is the gate.

## What to do when kitty itself blocks a behavior

Some behaviors are reachable only through the boss API (in-process), not through
`kitty @` (out-of-process). When `run.py` cannot reach the surface from outside
kitty, capture the gap in `repro.md`, archive the hypothesis as
`tmp/h<NN>-<slug>/blocked.md`, and open a follow-up OpenSpec change that scopes a
kitten promotion for that one capability — per the roadmap's Phase 3 promotion
criteria. Do not paper over the gap with a wrapper script.
