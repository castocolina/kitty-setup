## Why

Phase 2 §12 of `docs/requirements.md` asks for one-shot composition: from a daily shell, the user invokes a single command and ends up with a new tab containing a chosen layout + N pre-styled panes, each with its own title, optional per-pane background, and optional startup command. This is the first composition primitive in the Phase 2 line — it consumes the §8 title, §9 accent, §10 background, and §11 mirrored Tall primitives that already ship — and unblocks §13 (named scenes / TOML recipes) and §14 (chord-to-scene wiring), neither of which has a backend until §12 lands.

The h25 probe (`tmp/h25-scene-launcher/run.py`, green against kitty 0.46.2 on the user's daily host) settled five wire-level questions. The headline findings: `kitten @ launch --type=tab` combines tab-title + window-title + cwd + cmd in ONE call; the new tab is focused synchronously so subsequent `--type=window` calls land in it race-free; `--type=tab` returns the new tab's first WINDOW id (not the tab id), making `--match recent:0` the right tab handle; a full 3-pane scene completes in 6 kitten calls / ~85 ms — well within one human-perception frame. The proposal is grounded in those findings.

## What Changes

- **NEW CLI subcommand `my-kitty scene launch`** on the existing `my-kitty` binary. Imperative one-shot — invoked from any shell, opens a new tab + applies a layout + spawns N panes + sets per-pane and per-tab styling in one user gesture. Named-scene persistence (TOML recipes) is **out of scope** here; that's §13.
- **CLI shape (locked: Shape A from explore — `--pane key=value`):**
  ```
  my-kitty scene launch \
      [--layout=<name>[:<opts>]] \
      [--tab-title=<text>] [--tab-accent=<color>] \
      --pane 'key=value,key=value,...' \
      [--pane '...'] ...
  ```
  Each `--pane` value is a comma-separated `key=value` group. Recognised keys: `title`, `cmd`, `cwd`, `bg`. Commas inside values are escaped as `\,`. Each `--pane` becomes one `kitten @ launch --type=window` plus zero or one `set-colors` follow-up.
- **New Python module `src/kitty_setup/scenes/launcher.py`** — sibling of `title.py`, `accent.py`, `background.py`, `font.py`, `opacity.py`. Reuses the existing `_client.kitten_at()` helper for every kitten call (per-call socket discovery + error path inheritance) and the existing pgrep / `$KITTY_LISTEN_ON` discovery (no new wiring).
- **New CLI handler `cli_scene_launch`** wired into `cli.py` via a new top-level `scene` subparser and a `launch` sub-subcommand. Mirrors the existing `window title` / `tab accent` / `os-window font-size` dispatch shape.
- **Probe promoted to integration test.** `tmp/h25-scene-launcher/run.py` becomes `tests/integration/test_h25_scene_launcher.py`, gated on `KITTI_INTEGRATION=1`, with one named test per probe question (Q1-Q5). The probe directory is deleted on archive (mirrors the h22/h23/h24 contract).
- **Unit tests** under `tests/unit/test_scenes_launcher.py` covering the `--pane key=value` parser (including the comma-escape edge case), argv composition for kitten calls, and error paths (zero panes, invalid pane key, unknown layout).
- **Repro doc `docs/repro/h25-scene-launcher.md`** with the standard sections (Why, Manual repro, Linux Status, macOS Status, Attempted alternatives, Known limitations, Recipes).
- **No config-payload changes.** §12 is pure runtime CLI — it does not ship a new `.conf` file under `~/.config/kitty/kitty-setup/` and does not touch `kitty-setup.conf`. Chord wiring is §14.
- **No new doctor check.** Scene launching is a runtime gesture, not an install-time invariant.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kitty-scenes`: add the "Scene launcher composition primitive ships under `my-kitty scene launch`" Requirement, plus the standard h25 hypothesis-discipline + repro-doc Requirements (mirroring the h22 + h23 ADDED pattern in the archived deltas). No changes to existing primitive Requirements (title, accent, background, font, opacity, socket discovery, package layout) — the launcher composes on top of them via the same `_client.kitten_at()` surface.

## Impact

- **Affected code (new):**
  - `src/kitty_setup/scenes/launcher.py` — `Pane` dataclass, `parse_pane_spec()`, `launch_scene()` entry point, `cli_scene_launch` handler.
  - `tests/unit/test_scenes_launcher.py` — pane-spec parser tests + argv composition tests + error-path tests.
  - `tests/integration/test_h25_scene_launcher.py` — 5 named tests, one per probe question, all gated on `KITTI_INTEGRATION=1`.
  - `docs/repro/h25-scene-launcher.md` — repro doc.
- **Affected code (modified):**
  - `src/kitty_setup/cli.py` — add `scene` top-level subparser with one sub-subcommand (`launch`), wire to `cli_scene_launch` via `set_defaults(func=…)`. Argparse-native; no new dispatch shape.
- **Out of scope (explicit follow-ups):**
  - `phase2-named-scenes` (§13) — TOML recipe schema, scene name resolution, lookup from `~/.config/kitty-setup/scenes/`.
  - `phase2-chord-to-scene` (§14) — binding a curated chord to invoke either an imperative scene arg list or a named scene from §13.
  - macOS visual verification — deferred-with-reason in the repro doc; the `kitten @` protocol is platform-agnostic, but tab-bar rendering nuances may differ.
- **Performance:** 6 kitten calls for a 3-pane scene = ~85 ms total (h25 probe). No latency-driven kitten promotion is justified under the Phase 3 criterion ("subprocess and socket latency materially affects UX"). Scenes ship as scripts plus config.
