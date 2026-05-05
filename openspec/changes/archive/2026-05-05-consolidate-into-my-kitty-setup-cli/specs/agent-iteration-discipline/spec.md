## MODIFIED Requirements

### Requirement: Probe before assume (R6)

For every task in an OpenSpec change that depends on the behavior of an external CLI, an external API, an OS-level contract, or the syntax / semantics of a configuration file format that the repo does not own, a probe artifact SHALL exist before the task is executed. The probe MUST live at `tmp/probes/<change-id>/<NN>-<slug>.md`, where `<change-id>` is the kebab-case identifier of the OpenSpec change the probe belongs to and `<NN>` is a two-digit per-change ordinal restarting from `01` inside each change. The probe artifact MUST contain the six fields documented in `docs/probe-template.md`: assumption, command, exit code, output (relevant), verdict (one of `holds` / `fails` / `partial-with-workaround`), and used-by.

#### Scenario: Reviewer audits a task that calls an external CLI
- **WHEN** a reviewer reads a task in `tasks.md` that introduces or modifies code calling an external CLI
- **THEN** the reviewer SHALL find a probe under `tmp/probes/<change-id>/` (during the change's life) or referenced in the change's `## Probes` section in `design.md` (after archive) whose verdict supports the assumption the task encodes
- **AND** if no such probe exists, the reviewer SHALL block the change until one is added or the assumption is removed

#### Scenario: Author writes a probe for a single assumption
- **WHEN** an author needs to validate one assumption about an external system
- **THEN** the probe artifact SHALL contain exactly the six fields from `docs/probe-template.md` and SHALL fit on a single screen (target ≤ 50 lines)
- **AND** if the probe needs more than 50 lines or asks more than one question, the author SHALL convert it to a hypothesis under `tmp/h<NN>-<slug>/` instead

#### Scenario: Two changes have probes in flight at the same time
- **WHEN** two OpenSpec changes are concurrently in flight and each writes its own `01-...md` probe
- **THEN** the probes coexist without filename collision because they live under distinct `tmp/probes/<change-id>/` subdirectories

### Requirement: Design documents declare probes when external systems are touched

Any `design.md` whose change introduces tasks dependent on external CLI / API / OS / config-format behavior SHALL include a `## Probes` section. The section MUST list every probe the change depends on with: probe path (relative to repo root, e.g. `tmp/probes/<change-id>/01-<slug>.md`), assumption (one line), verdict, and the design decision the probe informs.

#### Scenario: Reviewer reads a design with no Probes section
- **WHEN** a reviewer reads a `design.md` for a change whose tasks call out external CLI or config-format behavior
- **THEN** the reviewer SHALL find a `## Probes` section listing each probe and its verdict
- **AND** if the section is missing, the reviewer SHALL block the change until either the section is added or the design is amended to remove the external-system dependencies

#### Scenario: Pure-Python or pure-doc change with no external probes
- **WHEN** a reviewer reads a `design.md` for a change whose tasks touch only repo-internal Python or repo-internal documentation
- **THEN** the `## Probes` section MAY be omitted entirely, OR included with a single line stating "No external assumptions; no probes required."

### Requirement: Probe vs hypothesis distinction is documented

`docs/agent-iteration.md` SHALL contain a callout that distinguishes probes (R6) from hypotheses (R1). Probes answer narrow questions about external-system shape ("does this CLI flag exist?", "what JSON does this command return?", "how does this config directive resolve relative paths?"). Hypotheses answer broader questions about user-observable behavior under our configuration ("does ctrl+shift+t open a tab inheriting the cwd?"). The callout SHALL state that probes go into `tmp/probes/<change-id>/<NN>-<slug>.md` (per-change subdirectory, single screen, six fields) and hypotheses go into `tmp/h<NN>-<slug>/` (a directory with `repro.md`, `run.py`, etc.).

#### Scenario: Reader of agent-iteration.md needs to choose probe vs hypothesis
- **WHEN** an agent reading `docs/agent-iteration.md` is unsure whether a question is a probe or a hypothesis
- **THEN** the agent SHALL find the probe-vs-hypothesis callout and SHALL be able to map their question to the correct artefact and template within one read
