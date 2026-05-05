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

### R6 — Probe before assume

Any task that depends on the behavior of an external CLI, an external API, an
OS-level contract, or the syntax / semantics of a configuration file format that
the repo does not own requires a probe artefact in
`tmp/probes/<change-id>/<NN>-<slug>.md` *before* the task is executed. Probes
live in a per-change subdirectory so concurrent in-flight changes don't collide
on `01-*.md`; the `<NN>` ordinal restarts at `01` inside each change. The probe
captures six fields: assumption (one line), command, exit code, relevant
output, verdict (`holds` / `fails` / `partial-with-workaround`), and the design
decision or code path that uses it. See
[docs/probe-template.md](probe-template.md) for the canonical shape.

Probes are scratch evidence. Their findings flow into `Why:` lines on `design.md`
decisions, into commit messages, or into source-code comments at the call site
that depends on them. Once a probe's finding is so encoded, the probe artefact
itself can be deleted with the rest of `tmp/` at the change's archive time.

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
evidence (in `tmp/probes/` while the change is live, or in the change's
`## Probes` section in `design.md` after archive).

If an integration test cannot be written today (the external system is not
available in the test environment, or its behavior cannot be triggered
synthetically), the stub is *provisional* and the change's task list MUST
include "build probe + integration test before promotion."

The bootstrap change's `tests/unit/test_config_updater.py` stubbed `kitty` with a
fake bash script that exited 0 unconditionally; the unit tests passed against an
imaginary `--debug-config` flag because no probe (R6) and no integration test
(R7) caught the gap. R7 makes that combination a review failure.

## Probes vs hypotheses

These are peers, not the same thing:

| Question shape | Artefact | Lives in | Size |
|---|---|---|---|
| "Does this CLI flag exist? What does this command return?" | **Probe** (R6) | `tmp/probes/<change-id>/<NN>-<slug>.md` | One screen, six fields |
| "Does this configuration produce this user-observable behavior?" | **Hypothesis** (R1) | `tmp/h<NN>-<slug>/` (directory) | repro.md + run.py + actual.json + draft.conf |

A probe answers a narrow factual question about external-system shape. A
hypothesis answers a broader question about how our configuration drives that
external system to produce the behavior the user wants. If a probe grows past
~50 lines or asks more than one question, it is a hypothesis in disguise — move
it to `tmp/h<NN>-<slug>/`.

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

3. **Probe any external assumption first.** Before the hypothesis directory is
   populated, walk the planned tasks and identify every external-system
   assumption (a CLI flag exists, a config directive accepts these values, an
   API returns this JSON shape). For each one, write a probe at
   `tmp/probes/<active-change>/<NN>-<slug>.md` per R6 and the
   [probe template](probe-template.md). The probe pass writes into the
   per-change subdirectory `tmp/probes/<active-change>/`. Wrong-shape probes
   get fixed here, in minutes, instead of getting fossilised into code or
   hypotheses that have to be ripped out later. Add a `## Probes` section to
   `design.md` listing each probe + verdict.

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
   - Move `repro.md` into `docs/repro/h<NN>-<slug>.md`.
   - Rewrite `run.py` as `tests/integration/test_h<NN>_<slug>.py` using pytest
     fixtures and the `KITTI_INTEGRATION` gate.
   - Encode every probe finding from step 3 into a durable location (`Why:` line
     in `design.md`, inline comment in source, or commit-message paragraph) per
     R6. The probe artefacts themselves stay in `tmp/probes/` and disappear with
     the rest of `tmp/` when the change archives.
   - Delete the `tmp/h<NN>-<slug>/` directory.

7. **Verify** end-to-end: `make doctor` exits 0 and `KITTI_INTEGRATION=1 make test`
   exits 0. Capture both outputs into the change's eventual PR description.

8. **Archive** the OpenSpec change with `openspec archive <name>`. The capability
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
