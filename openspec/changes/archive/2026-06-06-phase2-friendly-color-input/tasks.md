## 1. Color table + normalizer module

- [x] 1.1 Create `src/kitty_setup/scenes/_color_table.py` holding `COLOR_NAMES: dict[str, str]` (lowercase name → `#rrggbb`). Generate it once: **X11 `/usr/share/X11/rgb.txt` first (precedence), then CSS/SVG (PIL `ImageColor.colormap`, generation-time only) filling ONLY names X11 lacks** (teal/olive/lime/aqua/silver/fuchsia/indigo/crimson) + `rebeccapurple`. Result: 667 entries (658 X11 + 9 gap). Top-of-file comment records provenance. Include `grayN`/`greyN` (0–100) and both `gray`/`grey` spellings. Data-only module (no logic, no runtime import).
- [x] 1.2 Create `src/kitty_setup/scenes/colors.py`: `class ColorError(ValueError)`, and `normalize_color(value: str) -> str | None` implementing the design D2 resolution order — empty→`None`; `^#?[0-9a-f]{3}$|^#?[0-9a-f]{6}$` (case-insensitive)→ensure leading `#`; `NONE`/`rgb:`-prefixed/functional → passthrough; name in `COLOR_NAMES` → its hex; else raise `ColorError` naming the value with a hex + name example. Imports only stdlib + `_color_table`.
- [x] 1.3 Enumerate kitty's native named-color set on the host (sweep the `_color_table` keys via a throwaway kitty `set-colors`), assert `kitty_accepts ⊆ COLOR_NAMES` (the baked table is a superset). Capture the verdict in the repro doc; this is a one-time guard, not a shipped test that needs a live kitty.
- [x] 1.4 Add `colors` to the `from kitty_setup.scenes import (...)` export in `src/kitty_setup/scenes/__init__.py`.

## 2. Wire the normalizer into every color site

- [x] 2.1 `accent.py` (`my-kitty tab accent`): normalize the `<color>` positional and `--active-fg`/`--inactive-fg` via `normalize_color` before building the `set-tab-color` argv; map `ColorError` → stderr + exit 1, no kitten call. `NONE` passes through.
- [x] 2.2 `background.py` (`my-kitty window background`): normalize `<color>` before `set-colors`; `ColorError` → stderr + exit 1, no kitten call.
- [x] 2.3 **Central choke point** (design refinement during apply): instead of normalizing per-call-site, `launcher.launch_scene` normalizes `tab_accent` and every pane `bg` (via `dataclasses.replace`) at its very top, BEFORE the first `kitten @` call — covering BOTH the inline and named-recipe paths in one place. `recipe.load_scene` left unchanged; a bad recipe color surfaces as a `ColorError` raised by `launch_scene`.
- [x] 2.4 `launcher.py` cli helpers (`_launch_inline_scene` / `_launch_named_scene`) catch `ColorError` → stderr + exit 1, so a bad `--pane bg` / `--tab-accent` / recipe color rejects before any `kitten @ launch`. Verified: a multi-pane scene with one bad color opens zero windows (unit + e2e).
- [x] 2.5 Keep `Pane.bg` a plain `str` (already-normalized). No dataclass/schema change. Confirm the in-kitty fill-current-tab and new-tab paths both receive normalized values.

## 3. Unit tests `tests/unit/test_scenes_colors.py`

- [x] 3.1 Hashless hex: `fff`→`#fff`, `000`→`#000`, `ffffff`→`#ffffff`, `1A2B3C`→`#1a2b3c`; `#fff` unchanged; 4/5-char or non-hex char (`#ffzz`) → NOT treated as hex.
- [x] 3.2 Name translation: `teal`→`#008080`, `olive`→`#808000`, `lime`→`#00ff00`, `indigo`→`#4b0082`, `crimson`→`#dc143c`; case-insensitive (`Teal`).
- [x] 3.3 Collision-free known names: `green`→`#00ff00` (NOT `#008000`), `gray`→`#bebebe`, `purple`→`#a020f0`, `maroon`→`#b03060`; `grey`==`gray`, `grey50`==`gray50`.
- [x] 3.4 `NONE` passes through unchanged; `rgb:...` / functional forms pass through unchanged.
- [x] 3.5 Empty string → `None`.
- [x] 3.6 Unknown → `ColorError` whose message names the value and shows a hex + a name example (`notacolor`, `rebeccapurpel` typo).
- [x] 3.7 Per-site mapping (monkeypatch `kitten_at` with a guard that fails if called): `accent.py`/`background.py` cli handlers make NO kitten call on a bad color and exit 1; `launch_scene` raises `ColorError` before the first kitten call when any pane `bg` is bad; a gap-name `bg` (`teal`) appears in the `set-colors` argv as `#008080`.
- [x] 3.8 `pytest tests/unit/` fully green (zero regressions on existing accent/background/launcher/recipe tests).

## 4. Integration test `tests/integration/test_color_normalization_e2e.py`

- [x] 4.1 Gated on `KITTI_INTEGRATION=1`. `test_gap_name_applies`: `my-kitty window background teal` against a spawned kitty → `kitten @ get-colors` reads `background #008080` (a name kitty natively rejects now works end-to-end).
- [x] 4.2 `test_hashless_hex_applies`: `my-kitty window background 001a33` → `get-colors` reads `#001a33`.
- [x] 4.3 `test_bad_color_opens_no_window`: a multi-pane scene with `bg=notacolor` in pane 2 → exit non-zero AND `kitten @ ls` tab count unchanged (no window/tab opened).
- [x] 4.4 Run `KITTI_INTEGRATION=1 pytest tests/integration/test_color_normalization_e2e.py -v` on host — green.

## 5. Repro doc

- [x] 5.1 Create `docs/repro/friendly-color-input.md` (Why, Manual repro, Linux Status, macOS Status=deferred-with-reason, Attempted alternatives, Known limitations). Manual repro shows hashless hex, a gap name, and a rejected unknown opening no window. Record the 1.3 superset verdict. Note: no new `tmp/hNN` probe (deterministic value→value).

## 6. Verification

- [x] 6.1 `make doctor` clean (no new doctor check; confirm no regression).
- [x] 6.2 Full `make test` green; `KITTI_INTEGRATION=1` integration green on host; capture output for the handoff.
- [x] 6.3 `make format` / `ruff` / `pyright src` clean on the changed + new files.
- [x] 6.4 Update samples to showcase named colors where it reads better (e.g. `docker` tab_accent → `orange`), leaving deliberately-dark panel backgrounds in hex. Sync live `~/.config` copies.
- [x] 6.5 `openspec validate phase2-friendly-color-input --strict` passes.
