## ADDED Requirements

### Requirement: Copy strips end-of-line padding inserted by kitty's renderer

The system SHALL ensure that text copied from a kitty window into the system clipboard does NOT carry trailing whitespace that the user did not type. The copy path MUST behave like iTerm: a CLI command authored as `make build \` (one space, then a backslash for line-continuation) lands in the system clipboard as `make build \` (no trailing whitespace after the backslash), so that pasting it back into a shell preserves the line-continuation semantics.

The trailing-whitespace MUST be stripped on a per-line basis, before the bytes leave kitty for the system clipboard. Lines that intentionally end on a backslash, a quote, or any non-whitespace character MUST land in the clipboard with no padding after that final non-whitespace byte.

**Verification path:** `kitten @ get-text` returns kitty's logical line buffer and does NOT reproduce the regression — the renderer's column-width padding is applied only on the renderer→system-clipboard serialisation path (per probe-02). The autonomous probe MUST therefore exercise the real copy path: trigger a kitty copy action (`copy_to_clipboard`, `copy_last_command_output`, or equivalent that goes through the renderer) and read the resulting bytes via `wl-paste` (Wayland) or `xclip -selection clipboard -o` (X11).

#### Scenario: Backslash line-continuation lands in clipboard without padding
- **WHEN** an autonomous probe types a multi-line shell command into a `KittySession` whose lines end on `\` followed by `\n` (e.g. `make build \\\n    --target=foo\n`), triggers a kitty copy action that routes through the renderer (e.g. `copy_last_command_output` with `shell_integration enabled`), then reads the system clipboard via `wl-paste --no-newline` (or `xclip -selection clipboard -o` on X11)
- **THEN** the clipboard bytes contain the substring `make build \\\n    --target=foo` byte-for-byte — every backslash is immediately followed by `\n`, with NO whitespace inserted between the backslash and the newline

#### Scenario: Clean lines stay clean after copy
- **WHEN** an autonomous probe types `"echo hello\n"` into a `KittySession`, triggers the renderer-driven copy action, then reads the system clipboard
- **THEN** the clipboard bytes contain `"echo hello"` with NO inserted trailing whitespace between `hello` and the newline (or end-of-string, depending on the copy action's newline handling)

#### Scenario: Multi-line code block round-trips as a single executable command
- **WHEN** an autonomous probe types a 5-line shell command using `\` line-continuations on each non-final line into a `KittySession`, triggers the renderer-driven copy action, then writes the clipboard bytes to a temporary file and sources it via `bash <file>`
- **THEN** the script executes as a single command (the `\` line-continuations survive intact); the exit code is 0 and the script's combined stdout matches the expected single-command output

### Requirement: Copy preservation is delivered via config, not a wrapper

The configuration that delivers the trailing-whitespace strip MUST be expressible entirely in a single payload `*.conf` file under `~/.config/kitty/kitty-setup/` (loaded via the sentinel-bracketed include). The system MUST NOT depend on a shell wrapper, a kitten, a tmux config the system ships, or an out-of-tree helper script to achieve the strip. If the cause turns out to live outside kitty's reach (tmux clipboard rewrite, Wayland MIME plumbing), the remediation SHALL be documented in the repro doc as user-facing guidance, and this requirement remains UNMET — i.e. config-only fix is the bar for spec satisfaction.

Note: this requirement does NOT preclude the autonomous probe from depending on `shell_integration enabled` (a kitty config setting, not a shell wrapper) to use `copy_last_command_output` as the copy trigger. Shell-integration markers (OSC 133) are kitty-config territory; the requirement bars OUT-OF-TREE helpers, not in-config kitty features.

#### Scenario: Config alone is sufficient
- **WHEN** an integration test boots `KittySession` with the curated catalog appended to the session config and a `bash` shell with `shell_integration enabled` launched into it
- **THEN** the three trailing-whitespace-strip scenarios above pass without any shell-side configuration the user must add, no tmux config, no helper invocation

### Requirement: Linux-first delivery, macOS-deferred-with-note

The capability SHALL ship with a Linux-verified manual repro under `docs/repro/h17-paste-preservation.md`. The repro doc SHALL include a `## macOS Status` section that is either `verified` (with the macOS kitty version and date) or `deferred` (with a one-paragraph reason — e.g. no Mac access, blocked on a kitty surface bug). A `deferred` macOS Status SHALL NOT block merge; the capability SHALL NOT be declared "Phase 1 §4 complete" until the macOS Status is `verified`.

The Linux verification SHALL include a manual repro of the real mouse-select copy path (the autonomous probe uses a remote-control copy action which is a proxy, not the same byte path as a mouse-select copy). The manual repro asserts that copying a multi-line `\`-continuation command via mouse-select then pasting into a fresh shell produces a single executable command.

#### Scenario: Repro doc carries both status sections plus mouse-select manual repro
- **WHEN** the change merges
- **THEN** `docs/repro/h17-paste-preservation.md` exists with a `## Linux Status` section dated and verified (including the manual mouse-select repro outcome) and a `## macOS Status` section whose value is `verified` or `deferred`
