# kitty-scenes — Requirements (high-level)

Date: 2026-05-01. Clean restart. Hypothesis-driven, scripts before integration. Linux + macOS parity.

## Context
Previous attempt over-engineered before basics worked. New approach: prove each behavior with a small script against a real Kitty session, then promote stable scripts into config or a kitten. Two layers, independent: (1) a foundation of config + scripts that fix daily friction, (2) a scenes layer that builds themed tabs and windows from recipes. Either layer must be installable and removable on its own without breaking the other.

## Phase 1 — Foundation (config + scripts)
Items ordered easiest to hardest, by amount of Kitty surface touched, repro effort, and cross-platform fragility.
1. New tabs, windows, and splits inherit the cwd of the launching window.
2. One keybinding clears screen + scrollback instantly (iTerm Cmd+K parity, no `reset` delay).
3. Introspection command lists every active binding grouped by category, so conflicts are visible before they bite.
4. Paste preserves CLI output exactly — no trailing spaces on copied lines (regression vs iTerm).
5. Curated keybinding set, no conflicts, identical bindings on Linux and macOS for every chord except the instant-clear chord (which matches host-OS iTerm convention — Cmd+K on macOS, Super+K on Linux), covering at minimum: tabs (open/close/next/prev/move), windows (open/close/cycle), font zoom (+/-/reset), detach window or tab to another target, broadcast input across windows, URL hints.
6. Kitty survives suspend/resume and monitor disconnect — no crash, no exit.
7. Image-paste parity with iTerm — investigation. In iTerm (macOS) copying an image and pasting into a terminal-resident TUI such as Claude Code yields a `#[Image 1]` placeholder backed by a temp file path; Claude Code consumes it as an attachment. In Kitty on Pop OS Linux and on macOS (both observed under tmux), the same gesture produces nothing — only pasting the file path manually works. Goal: characterise the cause (Kitty clipboard MIME handling, tmux `set-clipboard` filtering, Wayland vs X11 clipboard-MIME exposure, or absence of an iTerm-style image-paste handler) and decide between three outcomes — (a) a Kitty config that fixes it (`clipboard_control`, `paste_actions`, `clipboard_max_size`), (b) a tmux-side fix, or (c) a small helper that reads the clipboard, writes the image to a temp file, and types its path. Document the workaround if (a)/(b) are not possible and ship it as the user-facing fix.

## Phase 2 — Scenes (one experiment script per item)
Same easy-to-hard ordering: single-property primitives first, composition and config-driven shapes last.
8. Apply title (text + emoji) to a window and to a tab.
9. Apply accent color to a tab so the role is identifiable at a glance, focused or not.
10. Apply background color, font, and transparency to a window.
11. Provide one extra layout orientation beyond Kitty defaults.
12. Launch a tab with a chosen layout, multiple pre-styled windows, and per-window startup commands ("scene").
13. Named, reusable building blocks. Define once, reference by name:
    - Window presets: a name binds a title (text + emoji), a theme (background, accent, font, transparency), and optional startup command. Example: `docker` → whale icon, blue accent, runs `docker ps`.
    - Tab presets: a name binds a tab title, accent color, and a layout. Example: `monitoring` → blue accent, vertical-split layout.
    - Scenes: a name binds a tab preset to an ordered list of window presets. Example: `docker-monitor` → `monitoring` tab with `docker-ps`, `docker-memory`, and one blank shell window.
14. Scenes are declarative recipes loaded from config, not ad-hoc invocations. Invocation is by scene name from a keybinding or remote-control command.

## Cross-cutting
- Per-component install and uninstall. Removing the foundation never touches scenes; removing scenes never touches the foundation.
- Diagnostic command reports whether the install is healthy: paths present, bindings parseable, Kitty version supported.
- Each requirement has a manual repro test documented next to its experiment script.
- Known limitation carried over: per-window opacity and per-window font size depend on Kitty boss surface that is global today; defer until verified.

## Sequencing
Phase 1 ships standalone and is dogfooded before Phase 2 starts. Within Phase 2, each item is a separate hypothesis script merged only after it works against a real Kitty session.

## Note — intent of the scenes layer
Kitty is the multitasking environment. The scenes layer exists so that a working mode can be summoned by name and recognized at a glance. Examples sketched by the user:
- `docker-monitor`: a tab on a multi-window layout with `docker ps`, `docker stats`, and one blank shell, tinted in a "monitoring" color so the tab is unmistakable.
- `ai-plan-review`: a tab with a vertical split running two AI assistants side by side for plan and review work.
- `ai-code-review`: same shape, different commands and accent.

The point is fast, visual orientation: which tab am I in, what is it for, and where do I go next. The exact mechanism — remote control calls, kitten, or something else — is a question to answer through experiment, not to lock in upfront.
