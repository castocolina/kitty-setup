# Agent Iteration Playbook

This is the operating manual for advancing kitty-setup one behavior at a time.
Read this before opening another phase plan or picking the next requirement from
[.planning/REQUIREMENTS.md](../.planning/REQUIREMENTS.md), in the phase order
[.planning/ROADMAP.md](../.planning/ROADMAP.md) sets. The rules here are not aspirational;
they are how the previous attempt did not fail again.

`AGENTS.md` is the canonical rule file. Where a rule appears both there and here, that file
states it and this one points at it; where they disagree, `AGENTS.md` wins. What this
playbook owns is the *hypothesis and probe layer* — the mechanics no rule file describes.

## Operating principles

### R1 — Investigate first

The rule is `AGENTS.md`'s "Hypothesis before implementation" bullet. What R1 adds is its
scope: no code lands in `src/`, `config/`, or `tests/integration/` until a hypothesis run in
`tmp/h<NN>-<slug>/` is green against a real kitty session, and that directory is the only
place where speculative code is allowed to live.

### R2 — Verify before declaring done

The rule is `AGENTS.md`'s "Verify before declaring done" bullet and is not restated here:
`make doctor` and `make test`, both **captured** rather than green, with their exit codes.
"Should work", "compiles", "looks right" are not evidence; the output of the verifying
command is. Capturing is the evidence duty, and it is a separate thing from the merge
precondition — `AGENTS.md`'s git policy additionally requires both commands to be green
before a phase branch merges, so a captured-but-red run satisfies this rule and still blocks
the merge.

What this playbook adds: for a hypothesis, the capture goes into the plan's SUMMARY beside
the green `actual.json`, so the next agent reads what was observed rather than what was
expected. Integration cases do not run at all without `KITTI_INTEGRATION=1`
(`tests/conftest.py`), so a capture that is meant to cover `tests/integration/` says which
form produced it — a bare `make test` reports green while skipping every one of them.

### R3 — Makefile is thin

Each Make target is at most five lines, including its banner. Anything longer is extracted
into a `my-kitty` subcommand under `src/kitty_setup/cli.py`, the single
`[project.scripts]` entry point — or into shell only where `AGENTS.md`'s `## Stack`
allow-list permits shell at all, which is the bootstrap pair `tools/setup.sh` /
`tools/uninstall.sh` and the git-invoked hook entry points under `tools/hooks/`. That
allow-list is stated once, in `AGENTS.md`, and is pointed at here rather than repeated, so
it cannot go stale in two places at once — it already had, which is how the hook files
Phase 1 added came to sit outside the allow-list as this document stated it. The Makefile is
glue, not logic.

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

### R6 — Probe before assume

Any task that depends on the behavior of an external CLI, an external API, an
OS-level contract, or the syntax / semantics of a configuration file format that
the repo does not own requires a probe artefact in
`tmp/probes/<phase>-<plan>/<NN>-<slug>.md` *before* the task is executed. Probes
live in a per-plan subdirectory so concurrent in-flight plans don't collide
on `01-*.md`; the `<NN>` ordinal restarts at `01` inside each plan. The probe
captures six fields: assumption (one line), command, exit code, relevant
output, verdict (`holds` / `fails` / `partial-with-workaround`), and the design
decision or code path that uses it. See
[docs/probe-template.md](probe-template.md) for the canonical shape.

Probes are scratch evidence. Their findings flow into the decisions section of the plan's
SUMMARY, into commit messages, or into source-code comments at the call site
that depends on them. Once a probe's finding is so encoded, the probe artefact
itself can be deleted with the rest of `tmp/` when the phase closes.

The bootstrap change paid the cost of skipping this rule three times: the
non-existent `kitty --debug-config` flag, the surprising relative-include
resolution, and the half-mirrored clear-binding probe each forced a full
rollback or fix cycle. R6 closes that gap.

### R7 — Test behavior, not mocks-of-assumptions

Unit tests under `tests/unit/` may stub external CLIs, APIs, or OS-level
contracts only when both of the following hold:

1. A probe per R6 confirms the real shape of the system being stubbed.
2. At least one integration test under `tests/integration/` exercises the real
   external system for the same code path covered by the stub.

The stub itself MUST carry a reference to the probe — either by a `_per_probe_<NN>`
suffix on the stub function name or by a one-line docstring naming the probe.
A future reader of the stub can then grep for the probe name and find the
evidence (in `tmp/probes/` while the plan is live, or in the plan's SUMMARY
`## Probes` section after the phase closes).

If an integration test cannot be written today (the external system is not
available in the test environment, or its behavior cannot be triggered
synthetically), the stub is *provisional* and the plan's task list MUST
include "build probe + integration test before promotion."

The bootstrap change's `tests/unit/test_config_updater.py` stubbed `kitty` with a
fake bash script that exited 0 unconditionally; the unit tests passed against an
imaginary `--debug-config` flag because no probe (R6) and no integration test
(R7) caught the gap. R7 makes that combination a review failure.

## Probes vs hypotheses

These are peers, not the same thing:

| Question shape | Artefact | Lives in | Size |
|---|---|---|---|
| "Does this CLI flag exist? What does this command return?" | **Probe** (R6) | `tmp/probes/<phase>-<plan>/<NN>-<slug>.md` | One screen, six fields |
| "Does this configuration produce this user-observable behavior?" | **Hypothesis** (R1) | `tmp/h<NN>-<slug>/` (directory) | repro.md + run.py + actual.json + draft.conf |

A probe answers a narrow factual question about external-system shape. A
hypothesis answers a broader question about how our configuration drives that
external system to produce the behavior the user wants. If a probe grows past
~50 lines or asks more than one question, it is a hypothesis in disguise — move
it to `tmp/h<NN>-<slug>/`.

## The loop

For every requirement a phase owns, repeat:

1. **Pick the next requirement** from [.planning/REQUIREMENTS.md](../.planning/REQUIREMENTS.md),
   in the phase order [.planning/ROADMAP.md](../.planning/ROADMAP.md) sets. Skip one only with
   a written reason in the phase's CONTEXT or in the plan that should have carried it.

2. **Open a phase plan** for it, under `.planning/phases/<NN>-<slug>/`. `/gsd-discuss-phase`
   then `/gsd-plan-phase` scaffold the artifacts that directory holds — CONTEXT (intent and
   locked decisions), RESEARCH and PATTERNS (the evidence), VALIDATION (the per-task
   verification map), and `<phase>-<plan>-PLAN.md` (the tasks) — and each plan carries
   `cross_ai: true` per `AGENTS.md`. The requirements a plan satisfies are named in its
   frontmatter, which is what makes `.planning/REQUIREMENTS.md`'s traceability table
   checkable. There is no separate capability spec to maintain: `.planning/` is the single
   source of truth, and `.planning/legacy/openspec/` is frozen history that is never a
   destination.

3. **Probe any external assumption first.** Before the hypothesis directory is
   populated, walk the planned tasks and identify every external-system
   assumption (a CLI flag exists, a config directive accepts these values, an
   API returns this JSON shape). For each one, write a probe at
   `tmp/probes/<phase>-<plan>/<NN>-<slug>.md` per R6 and the
   [probe template](probe-template.md). The probe pass writes into the
   per-plan subdirectory `tmp/probes/<phase>-<plan>/`. Wrong-shape probes
   get fixed here, in minutes, instead of getting fossilised into code or
   hypotheses that have to be ripped out later. List each probe and its verdict in a
   `## Probes` section of the plan's SUMMARY.

4. **Drop scratch** into `tmp/h<NN>-<slug>/`:
   - `repro.md` — what the behavior is, the manual repro steps, the expected
     observable outcome (cwd is `/tmp`, screen is empty, etc).
   - `run.py` — an autonomous probe using `kitty_setup.harness.KittySession` that
     drives a real kitty session and asserts the expected outcome.
   - `expected.json` — a structured form of the expected outcome (often the
     interesting subset of `kitty @ ls` output).
   - `actual.json` — captured by `run.py` on the latest run; gitignored.
   - `draft.conf` — the candidate kitty config snippet being iterated on.

5. **Iterate** the candidate `draft.conf` until `run.py` is green. Capture the green
   `actual.json` so the next agent can see what was observed.

6. **Promote** by hand:
   - Move the proven snippet into `config/kitty/<topic>.conf` (creating the file if
     needed). Update `config/kitty/kitty-setup.conf` to `include` it.
     **File basename = binding category.** `windowing.conf` → "windowing"
     section in `my-kitty keys`; `clear.conf` → "clear" section. Pick a
     filename you would want to see as a section header in the introspection
     report.
   - Move `repro.md` into `docs/repro/h<NN>-<slug>.md`.
   - Rewrite `run.py` as `tests/integration/test_h<NN>_<slug>.py` using pytest
     fixtures and the `KITTI_INTEGRATION` gate.
   - Encode every probe finding from step 3 into a durable location (a `Why:` line in the
     plan's SUMMARY, an inline comment at the dependent call site, or a commit-message
     paragraph) per R6. The probe artefacts themselves stay in `tmp/probes/` and disappear
     with the rest of `tmp/` when the phase closes.
   - Delete the `tmp/h<NN>-<slug>/` directory.

7. **Verify** end-to-end per R2: run `make doctor` and `make test`, and capture both
   outputs with their exit codes into the plan's SUMMARY. `make test-integration` is the
   form that actually executes `tests/integration/`: it runs them headless under a nested
   compositor, so no window reaches the desktop, and it fails rather than skips when no
   compositor exists. A promotion that added an integration test says which form it
   ran. Green is the merge precondition `AGENTS.md`'s
   git policy states; capturing is this rule.

8. **Close the plan**: write `.planning/phases/<NN>-<slug>/<phase>-<plan>-SUMMARY.md` —
   what landed, every deviation from the plan, the captured evidence — then advance
   `.planning/STATE.md` and the phase's row in `.planning/ROADMAP.md`. The phase directory
   *is* the archive; nothing is moved anywhere else.

## Hand-off across agents

The agent that writes a hypothesis is *not* the same agent that promotes it. This is
`AGENTS.md`'s primacy of the planning artifacts — they are authoritative and are never
rewritten to match what drifted — applied to the hypothesis layer. Concretely:

- The agent that authors `tmp/h<NN>-<slug>/run.py` and gets it green leaves the
  green `actual.json` and an updated `repro.md` describing what it observed.
- A separate agent reads the green hypothesis, decides whether the captured
  evidence justifies promotion, and performs the manual rewrite into `src/`,
  `config/`, `docs/repro/`, and `tests/integration/`.
- If the second agent disagrees with the hypothesis, it amends `repro.md` with
  the disagreement and the work goes back to step 4 with a new hypothesis.

## What to do when the harness disagrees with the manual repro

The autonomous probe is the source of truth. If the manual repro says a behavior
works and the autonomous probe says it does not, the behavior does not ship. Either
the probe is wrong (fix the probe) or the behavior is wrong (fix the config). The
manual repro is documentation; the probe is the gate.

## What to do when kitty itself blocks a behavior

Some behaviors are reachable only through the boss API (in-process), not through
`kitty @` (out-of-process). When `run.py` cannot reach the surface from outside
kitty, capture the gap in `repro.md`, park the hypothesis as
`tmp/h<NN>-<slug>/blocked.md`, and record the gap where the next milestone will see it — a
requirement candidate in `.planning/REQUIREMENTS.md`, or a phase via `/gsd-phase`. Kitten
promotion is explicitly out of scope for this milestone (`.planning/PROJECT.md`,
`.planning/REQUIREMENTS.md` "Out of Scope"), so promoting one is a new-milestone decision,
not a mid-phase one. Do not paper over the gap with a wrapper script.
