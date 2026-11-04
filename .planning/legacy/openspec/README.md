# OpenSpec (frozen)

> **FROZEN — history only; source of truth is `.planning/`.**
> Superseded by `.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md`. Retained for provenance; do not edit.

Date: 2026-09-23. This tree was the OpenSpec root for kitty-setup until the
phase-1 governance freeze. The pending change
`phase1-curated-bindings-revert-defaults` was retired with `openspec archive
… --skip-specs -y`, so the main specs under `specs/` were never synced and
remain byte-identical to their pre-archive state; the archived change — spec
deltas included — lives under `changes/archive/2026-09-23-phase1-curated-bindings-revert-defaults/`.
A whole-tree `openspec validate` is knowingly not green: twelve pre-existing
findings across unrelated specs predate this phase, and rewriting frozen specs
is out of scope. The live source of truth is `.planning/`, specifically
`.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md`.
