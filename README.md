# kitty-setup

Hypothesis-driven toolkit for the [Kitty terminal](https://sw.kovidgoyal.net/kitty/),
delivered in two independent components that share a repo:

- **Foundation** — Kitty config plus small scripts that fix daily friction (suspend/resume
  stability, paste fidelity, cwd-preserving tabs/windows, instant clear-screen, a curated
  cross-platform keybinding set, binding introspection, an install diagnostic).
- **Scenes** — declarative recipes that summon a themed working mode by name: a tab with a
  chosen layout, multiple pre-styled windows, and per-window startup commands. Examples:
  `docker-monitor`, `ai-plan-review`, `ai-code-review`.

> **Status**: Phase 0 — clean restart. Foundation work has not started yet. There is no
> installable artifact in this repo today. Scope and roadmap are public so the design can
> be reviewed before code lands.

Linux + macOS parity is non-negotiable. Every shipped behavior is verified on both.


