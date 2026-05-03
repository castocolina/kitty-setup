## 1. Update `docs/agent-iteration.md`

- [x] 1.1 Add R6 (Probe before assume) to the "Operating principles" section, with the same heading shape as R1–R5 (numbered, short prose, justification, link to template).
- [x] 1.2 Add R7 (Test behavior, not mocks-of-assumptions) to the "Operating principles" section.
- [x] 1.3 Add a "Probes vs hypotheses" callout (a short subsection) that distinguishes probes (single screen, `tmp/probes/<NN>.md`, six fields, narrow shape question) from hypotheses (`tmp/h<NN>-<slug>/`, multi-file scratch, broad behavior question). Cross-link to `docs/probe-template.md` and to the existing R1 hypothesis playbook.
- [x] 1.4 Update "The loop" so step 3 (drop scratch into `tmp/h<NN>-<slug>/`) is preceded by step 2.5 (probe any external-system assumption that the hypothesis depends on, drop it into `tmp/probes/<NN>.md`).

## 2. Add `docs/probe-template.md`

- [x] 2.1 Author the canonical probe template with the six fields from D2 (assumption, command, exit code, output, verdict, used-by). Include one fully filled-in example using the `kitty --debug-config` failure from the bootstrap change as illustration.
- [x] 2.2 State explicitly: target ≤ 50 lines per probe; anything bigger becomes a hypothesis under `tmp/h<NN>-<slug>/`.

## 3. Verify the change is internally consistent

- [x] 3.1 Run `openspec validate tighten-probe-first-discipline --strict` and confirm "Change is valid".
- [x] 3.2 Read the updated `docs/agent-iteration.md` end-to-end and confirm the new rules read as peers to R1–R5 (no orphaned references, numbering consistent).
- [x] 3.3 Read `docs/probe-template.md` end-to-end and confirm an agent can copy the template, fill it in, and produce a probe artefact in under five minutes.
- [x] 3.4 Confirm `git status` shows exactly the expected modifications (`docs/agent-iteration.md`) and additions (`docs/probe-template.md`, `openspec/changes/tighten-probe-first-discipline/*`); nothing else.

## 4. Commit + archive

- [x] 4.1 Two commits: `docs(openspec): propose tighten-probe-first-discipline` (the change scaffold) and `docs(agents): add R6 + R7 + probe template` (the applied doc updates). Use HEREDOC for messages.
- [x] 4.2 `openspec archive tighten-probe-first-discipline -y` to land the `agent-iteration-discipline` capability in `openspec/specs/`. One trailing commit: `docs(openspec): archive tighten-probe-first-discipline, sync specs`.
- [x] 4.3 Confirm `openspec list` reports zero active changes and `openspec/specs/agent-iteration-discipline/spec.md` exists with all five requirements.
