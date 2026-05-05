# Probe Template

Canonical shape for every probe artefact under
`tmp/probes/<change-id>/<NN>-<slug>.md`. The `<change-id>` subdirectory is the
kebab-case identifier of the OpenSpec change the probe belongs to; the `<NN>`
ordinal restarts at `01` per change. This avoids filename collisions when two
changes have probes in flight at the same time.

A probe answers a single, narrow factual question about an external CLI, an
external API, an OS-level contract, or the syntax / semantics of a configuration
file format that this repo does not own. Probes exist to keep code from being
written against an *imagined* contract — they make the cost of catching a wrong
assumption "60 seconds and one shell command" instead of "one rollback cycle".

Probes are scratch. They live under `tmp/` (gitignored) and disappear when the
owning OpenSpec change archives. Their *findings* are durable: those flow into a
`Why:` line on a `design.md` decision, an inline comment at the dependent code
site, or a paragraph in the change's commit message. See R6 in
[agent-iteration.md](agent-iteration.md) for the rule and
[openspec/specs/agent-iteration-discipline/spec.md](../openspec/specs/agent-iteration-discipline/spec.md)
for the spec.

## Format — six fields, single screen

```markdown
# Probe NN — <one-line slug>

**Assumption:** <single declarative sentence stating what you believe is true>
**Command:** <exact shell command, copy-pasteable>
**Exit code:** <integer>
**Output (relevant):** <short excerpt or fenced block; trim aggressively>
**Verdict:** holds | fails | partial-with-workaround
**Used by:** <design decision or code path that depends on this finding>
```

Target ≤ 50 lines total. If you need more — multiple commands, multiple
verdicts, a non-trivial environment to reproduce — your question is a hypothesis,
not a probe. Move it to `tmp/h<NN>-<slug>/` (a directory; per-repo numbering, not
per-change) and follow R1.

## Filled-in example

The following probe is the one the bootstrap change *should have written* before
authoring `src/kitty_setup/config_updater.py`. It would have caught the
non-existent `--debug-config` flag in 60 seconds instead of after a full
rollback cycle.

```markdown
# Probe 01 — does kitty 0.46 expose --debug-config?

**Assumption:** kitty 0.46.x supports a `--debug-config --config <file>` invocation
that exits 0 on a parseable config and non-zero on a malformed one, the way
older Kitty versions did.

**Command:**
```sh
~/.local/kitty.app/bin/kitty --help 2>&1 | grep -E '(debug-config|debug.*config)'
```

**Exit code:** 1

**Output (relevant):**
(empty — `grep` matched nothing)

**Verdict:** fails

**Used by:** `src/kitty_setup/config_updater.py` parse-check. Implication:
switch to `kitty +runpy "from kitty.config import load_config; ..."` with the
`accumulate_bad_lines=` argument to drive the same signal. Documented in
`design.md` D2 ("After every mutation, run …").
```

## How to write one quickly

1. Name the assumption in one sentence. If you can't, the question is too broad
   for a probe.
2. Pick the smallest command that proves or disproves the assumption. `--help`
   greps, single `+runpy` snippets, single `curl` calls. No pipelines unless
   the pipeline IS the assumption.
3. Run the command. Copy its exit code and the *relevant* slice of its output
   (not all of it).
4. Write the verdict. Use exactly one of `holds`, `fails`,
   `partial-with-workaround`. If you reach for "kind of" or "it depends",
   the question was too broad — split the probe in two.
5. Name what depends on this finding. If nothing depends on it, you didn't need
   the probe.

## Where probe findings end up

The probe artefact itself is throwaway. Its finding is durable and lands in
exactly one of these places:

* **`Why:` line on a decision in `design.md`** — when the finding influenced
  an architectural choice. Add a `## Probes` section to `design.md` listing
  the probe + verdict so reviewers can scan the evidence trail.
* **Inline comment in source code** — when the finding only matters at one
  call site. Format: `# probe-<change-id>-<NN>: <assumption verdict>`.
* **Paragraph in the change's commit message** — when the finding shaped the
  commit's reasoning but doesn't fit either of the above.

A change whose `## Probes` section lists probes whose findings are NOT encoded
into one of these durable locations cannot archive (per R6 and the
`agent-iteration-discipline` spec).
