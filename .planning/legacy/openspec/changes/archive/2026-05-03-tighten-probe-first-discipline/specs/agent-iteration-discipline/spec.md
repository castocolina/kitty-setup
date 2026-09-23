## ADDED Requirements

### Requirement: Probe before assume (R6)

For every task in an OpenSpec change that depends on the behavior of an external CLI, an external API, an OS-level contract, or the syntax / semantics of a configuration file format that the repo does not own, a probe artifact SHALL exist before the task is executed. The probe MUST live at `tmp/probes/<NN>-<slug>.md`, where `<NN>` is a two-digit per-change ordinal restarting from `01` inside each change. The probe artifact MUST contain the six fields documented in `docs/probe-template.md`: assumption, command, exit code, output (relevant), verdict (one of `holds` / `fails` / `partial-with-workaround`), and used-by.

#### Scenario: Reviewer audits a task that calls an external CLI
- **WHEN** a reviewer reads a task in `tasks.md` that introduces or modifies code calling an external CLI
- **THEN** the reviewer SHALL find a probe under `tmp/probes/` (during the change's life) or referenced in the change's `## Probes` section in `design.md` (after archive) whose verdict supports the assumption the task encodes
- **AND** if no such probe exists, the reviewer SHALL block the change until one is added or the assumption is removed

#### Scenario: Author writes a probe for a single assumption
- **WHEN** an author needs to validate one assumption about an external system
- **THEN** the probe artifact SHALL contain exactly the six fields from `docs/probe-template.md` and SHALL fit on a single screen (target ≤ 50 lines)
- **AND** if the probe needs more than 50 lines or asks more than one question, the author SHALL convert it to a hypothesis under `tmp/h<NN>-<slug>/` instead

### Requirement: Test behavior, not mocks-of-assumptions (R7)

Unit tests in `tests/unit/` MAY stub external CLIs, APIs, or OS-level contracts only when both of the following hold: (a) a probe per R6 confirms the real shape of the system being stubbed, AND (b) at least one integration test under `tests/integration/` exercises the real external system for the same code path covered by the stub. The stub itself MUST carry a reference to the probe — either in the stub function's name (suffix `_per_probe_<NN>`) or in a one-line docstring naming the probe.

#### Scenario: Unit test stubs an external CLI without a probe
- **WHEN** a reviewer reads a unit test that stubs an external CLI binary or API client
- **THEN** the reviewer SHALL grep for the probe reference (in the stub name or docstring) and find a corresponding probe artifact whose verdict supports the stubbed behavior
- **AND** if the reviewer finds no probe reference, the change SHALL be blocked until either the stub is annotated or the stub is replaced with a real call to the external system

#### Scenario: Unit test stubs an external CLI without an integration test
- **WHEN** a reviewer reads a unit test that stubs an external CLI binary or API client
- **THEN** the reviewer SHALL find at least one integration test under `tests/integration/` that exercises the same code path against the real external system
- **AND** if no integration test exists, the change SHALL document why the integration test is impossible today and SHALL list "build integration test before promotion" in the relevant tasks before being archived

### Requirement: Design documents declare probes when external systems are touched

Any `design.md` whose change introduces tasks dependent on external CLI / API / OS / config-format behavior SHALL include a `## Probes` section. The section MUST list every probe the change depends on with: probe path (relative to repo root, e.g. `tmp/probes/01-kitty-debug-config.md`), assumption (one line), verdict, and the design decision the probe informs.

#### Scenario: Reviewer reads a design with no Probes section
- **WHEN** a reviewer reads a `design.md` for a change whose tasks call out external CLI or config-format behavior
- **THEN** the reviewer SHALL find a `## Probes` section listing each probe and its verdict
- **AND** if the section is missing, the reviewer SHALL block the change until either the section is added or the design is amended to remove the external-system dependencies

#### Scenario: Pure-Python or pure-doc change with no external probes
- **WHEN** a reviewer reads a `design.md` for a change whose tasks touch only repo-internal Python or repo-internal documentation
- **THEN** the `## Probes` section MAY be omitted entirely, OR included with a single line stating "No external assumptions; no probes required."

### Requirement: Probe findings outlive the probe directory

Probe artifacts under `tmp/probes/` are gitignored and SHALL NOT be promoted to a permanent location in the repository. Findings from probes (the verdicts and the implications they have for code) SHALL be encoded into one of the following durable locations: a `Why:` line on a decision in `design.md`, a comment at the call site in source code that depends on the assumption, or a paragraph in the change's commit message. A probe whose finding is not encoded into a durable location before the change archives SHALL block the archive.

#### Scenario: Reviewer audits a change about to archive
- **WHEN** a reviewer prepares to run `openspec archive <change>` on a change whose `## Probes` section is non-empty
- **THEN** the reviewer SHALL verify that every probe verdict has a corresponding `Why:` line in `design.md`, an inline comment at the dependent code site, or a paragraph in the change's commit message
- **AND** if any probe finding is not so encoded, the archive SHALL be blocked until the finding is captured durably

### Requirement: Probe vs hypothesis distinction is documented

`docs/agent-iteration.md` SHALL contain a callout that distinguishes probes (R6) from hypotheses (R1). Probes answer narrow questions about external-system shape ("does this CLI flag exist?", "what JSON does this command return?", "how does this config directive resolve relative paths?"). Hypotheses answer broader questions about user-observable behavior under our configuration ("does ctrl+shift+t open a tab inheriting the cwd?"). The callout SHALL state that probes go into `tmp/probes/<NN>-<slug>.md` (single screen, six fields) and hypotheses go into `tmp/h<NN>-<slug>/` (a directory with `repro.md`, `run.py`, etc.).

#### Scenario: Reader of agent-iteration.md needs to choose probe vs hypothesis
- **WHEN** an agent reading `docs/agent-iteration.md` is unsure whether a question is a probe or a hypothesis
- **THEN** the agent SHALL find the probe-vs-hypothesis callout and SHALL be able to map their question to the correct artefact and template within one read
