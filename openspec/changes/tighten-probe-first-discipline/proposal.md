## Why

The bootstrap change (`bootstrap-foundation-phase1-popos`) shipped, but along the way three failures landed in code before being caught: (1) `kitty --debug-config` was assumed to exist when kitty 0.46+ has no such flag, (2) include-path resolution semantics inside our own config payload were assumed but not checked, (3) the H02 probe invoked only one half of the binding's `combine`. Each failure burned an extra rollback or fix cycle. The existing R1 ("investigate first") covers hypothesis dirs for *behaviors* but not the smaller, earlier question — does the external CLI / API / config syntax that I'm about to write code against actually behave the way I'm assuming? We need a discipline rule for that, and a place to record the evidence.

## What Changes

- Add **R6 — Probe before assume** to `docs/agent-iteration.md`: any task that depends on external CLI behavior, config syntax, or OS-API contract requires a probe artifact in `tmp/probes/<NN>-<slug>.md` BEFORE the task is written or executed. Probes capture: assumption (one line), command run, exit code, relevant stdout/stderr, verdict (holds / fails / partial-with-workaround). Findings flow into `Why:` lines on `design.md` decisions or as comments on the code that depends on them.
- Add **R7 — Test behavior, not mocks-of-assumptions** to `docs/agent-iteration.md`: unit tests may stub external CLIs only when (a) a probe (R6) confirms the real shape AND (b) an integration test exists that exercises the real CLI for the same code path. Stub names reference the probe (`fake_kitty_per_probe_07`). If the integration test cannot be written today, the stub is provisional and the task list MUST include "build probe + integration test before promotion."
- Document a `## Probes` section as a recommended sub-section of `design.md` for any change whose tasks touch external systems. The section lists each probe with: assumption, probe path, verdict, and the design decision the probe informs.
- Add `docs/probe-template.md` — a one-page filled-in template a probe author can copy into `tmp/probes/<NN>-<slug>.md`. Template owns the canonical shape so probe quality does not drift.
- Update `.gitignore` and `tmp/probes/` is already covered by the `tmp/` rule from the bootstrap change.

## Capabilities

### New Capabilities

- `agent-iteration-discipline`: workflow-level rules that govern how OpenSpec changes are proposed, designed, executed, and reviewed in this repo. The "system" being specified is the development workflow itself; "scenarios" are review checkpoints (a reviewer reading a change can verify the rule held). This change introduces the probe-first discipline (R6, R7) as the first set of requirements under this capability.

### Modified Capabilities

None. The bootstrap change's five capabilities (kitty-install, kitty-config-management, kitty-test-harness, kitty-cwd-inheritance, kitty-instant-clear) are not touched — this is a pure process change.

## Impact

- **Edited files**: `docs/agent-iteration.md` (R6 + R7 + Probes section pointer).
- **New files**: `docs/probe-template.md`.
- **Edited specs**: a new `openspec/specs/agent-iteration-discipline/spec.md` lands when this change is archived.
- **Behavior**: no kitty behavior changes. No source code changes. No runtime dependency changes.
- **Cost paid**: every future change with external-system tasks will have one probe-writing step per assumption. Cheap (a probe is a one-liner shell command + a verdict line) compared to the per-failure rollback cost the bootstrap absorbed.
- **Out of scope**: retroactively writing probe artifacts for the bootstrap change. The lessons are captured in the bootstrap change's tasks-as-changelog (commit `2c0fb4b`); rewriting history is not the point.
