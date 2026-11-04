## Context

The bootstrap change proved out the hypothesis-driven workflow at the *behavior*
layer (R1: every shipped behavior begins as `tmp/h<NN>-<slug>/`). It did not have a
discipline rule for the smaller, earlier question that bit it three times: does the
external CLI / API / config syntax I'm about to write code against actually behave
the way I'm assuming? Specifically:

* **Failure 1** — `src/kitty_setup/config_updater.py` was written invoking
  `kitty --debug-config` based on a memory of older Kitty docs. Kitty 0.46.2 has
  no such flag. Caught only when `make setup` rolled back.
* **Failure 2** — the include path inside our payload (`include kitty-setup/windowing.conf`)
  was written without checking how Kitty resolves relative includes (relative to
  the file being parsed, not to `~/.config/kitty/`). Caught at parse time.
* **Failure 3** — the H02 probe initially invoked only the `clear_terminal scrollback active`
  half of the binding's `combine`, missing the `send_text \x0c` half. Caught when
  the assertion failed.

Each failure was a one-cycle rollback or fix, but they share a shape: code (or a probe)
shipped against an *imagined* contract instead of a *checked* contract. The unit-test
suite for `config_updater.py` even stubbed Kitty with a fake bash script that exited 0
unconditionally, so the unit tests passed against the imaginary `--debug-config` flag.

This change formalises a discipline rule that closes that gap, plus a documentation
artefact (the probe template) that makes following the rule cheap.

## Goals / Non-Goals

**Goals:**

* Land R6 (probe before assume) and R7 (test behavior, not mocks-of-assumptions) in
  `docs/agent-iteration.md` as numbered, peer rules to R1–R5.
* Make the probe artefact format canonical via `docs/probe-template.md` so every probe
  in `tmp/probes/` has the same shape and a future reviewer can scan it in seconds.
* Document the recommended `## Probes` section for `design.md` so reviewers can see,
  up-front, which assumptions in a change have evidence vs which are speculative.
* Capture the discipline as testable (review-checkable) requirements under a new
  `agent-iteration-discipline` capability so future regressions on the rule can be
  flagged in code review against the spec.

**Non-Goals:**

* No retroactive probes for the bootstrap change. The lessons are captured inline in
  the bootstrap's tasks-as-changelog (commit `2c0fb4b`); rewriting history is not the
  point.
* No automated enforcement (no pre-commit hook, no CI check). Reviewer-enforced for
  now; automation is a follow-up change if the rule drifts.
* No change to `R1`–`R5`. Probes complement hypotheses; they do not replace them.
* No new code. This change is doc + spec only.
* No retroactive change to bootstrap commits. We do not amend published commits.

## Decisions

### D1 — Probes live under `tmp/probes/<NN>-<slug>.md`, gitignored

Probes are scratch evidence. They go under `tmp/`, which is already gitignored by
the bootstrap change. They are NOT promoted to a permanent location; their findings
flow into `Why:` lines in `design.md`, into commit messages, or into source-code
comments at the call site that depends on them.

Alternative considered: keep probes in `docs/probes/` permanently. Rejected — the
artefact value decays the moment its assumption is encoded into code; keeping the
file forever invites stale-evidence rot. The *finding* is what matters, and it has
to land somewhere durable (design or code).

Numbering (`<NN>`) is per-change, restarting from 01 inside each change's lifetime,
to keep the namespace local and avoid coordination headaches. A probe referenced by
code uses the form `probe-<change-id>-<NN>` so the reference still resolves once
the probe directory is gone.

### D2 — Probe template is one Markdown file, six fields

```
# Probe NN — <one-line slug>

**Assumption:** <single sentence>
**Command:** <exact command, copy-pasteable>
**Exit code:** <integer>
**Output (relevant):** <short excerpt or full block>
**Verdict:** holds | fails | partial-with-workaround
**Used by:** <design decision or code path that depends on this>
```

Anything beyond these six fields is bloat. Probes that need more than this are
hypotheses, not probes — they belong in `tmp/h<NN>-<slug>/`.

Alternative: TOML/YAML structured probe. Rejected — Markdown is the medium reviewers
already read; structured formats add tooling cost for no review benefit at this scale.

### D3 — `## Probes` is a recommended, optional section in `design.md`

It is not added to the openspec schema (no risk of making *every* design document carry
the section even when a change has no external assumptions). It is documented in
`docs/agent-iteration.md` and in the probe template as "include this section in your
design when your change touches external systems."

Alternative: enforce the section in the openspec schema. Rejected — would force
ceremony onto pure-Python or pure-doc changes that have no external assumptions to probe.

### D4 — `agent-iteration-discipline` is the right capability home

We modeled five capabilities for the kitty foundation; we do not have a capability
for "how we work." Adding `agent-iteration-discipline` gives the discipline rules a
spec home with the same review surface as behavior contracts. Each rule becomes a
SHALL requirement; the scenarios are review checkpoints (e.g., "WHEN reviewer reads
a unit-test stub of an external CLI, THEN reviewer SHALL find a probe link in the
test's docstring or in the same change's `## Probes` section").

Alternative: keep this purely in `docs/` without an openspec spec. Rejected —
process documentation drifts; openspec specs are the artefact whose drift is most
likely to be noticed (because every future change references them).

### D5 — Stub-naming convention encodes traceability

Test stubs that mock external CLI behavior are named with a `_per_probe_<NN>` suffix
or carry a one-line docstring naming the probe. This means a future reader of a
stubbed test can grep for the probe name and find the evidence (in `tmp/probes/`
during the change's life, or in the design's `## Probes` section after archive).

Alternative: rely on docstring discipline alone. Rejected — names are searchable;
docstrings are not always read.

## Risks / Trade-offs

* **Risk: ceremony fatigue.** Authors skip probes for "obvious" assumptions; rule decays.
  → *Mitigation:* probe template is six fields. A probe for `kitty --help | grep
  debug-config` takes 60 seconds end to end. Reviewer pushback on changes whose
  `## Probes` section is empty despite touching external systems is the gating force.
* **Risk: probes drift from the assumption they document.** A probe written months ago
  no longer reflects current external behavior.
  → *Mitigation:* probes are scoped to a single change. They are gitignored and gone
  once the change archives. Only the finding (encoded in design or code) persists,
  and the finding is what the integration test exercises against the real system.
* **Risk: people confuse probes with hypotheses (R1).** Probe = "does this CLI flag
  exist?" Hypothesis = "does this configuration produce this user-observable behavior?"
  → *Mitigation:* `docs/agent-iteration.md` adds a "probe vs hypothesis" callout. The
  template's six-field constraint forces small scope; anything bigger gets pushed to
  `tmp/h<NN>-<slug>/`.
* **Trade-off: reviewer-only enforcement, not CI.** Drift is possible.
  → *Mitigation:* accepted for now. If two future changes ship without probes against
  external assumptions, open a follow-up change to add a pre-commit hook that scans
  `tmp/probes/` for the active change.

## Migration Plan

This is a doc + spec change with no runtime side effects. No migration is required.

Deploy:

1. Land `docs/agent-iteration.md` updates (R6, R7, probe-vs-hypothesis callout).
2. Land `docs/probe-template.md`.
3. Land the new `agent-iteration-discipline` spec when this change archives.

Rollback: revert the commits. No state changes anywhere on disk outside the repo.

## Open Questions

* **Q1 — Should the probe template enforce a maximum byte size?** Probes that grow
  past ~50 lines tend to be hypotheses in disguise. We could refuse probes over a
  size cap. *Decision:* not in this change. Watch the first five probes; revisit if
  any blow past 50 lines without being moved to `tmp/h<NN>-<slug>/`.
* **Q2 — Do we want a `make probes` target that lists probes for the active change?**
  Useful when the active-change directory becomes the canonical home for in-progress
  probes. *Decision:* deferred. Worth doing once two or more concurrent changes coexist.
