## 1. Alpha-strip in `normalize_color` (#4)

- [x] 1.1 Widen `_HEX_RE` in `scenes/colors.py` to also match 4- and 8-digit hex (`^#?[0-9a-f]{4}$`, `^#?[0-9a-f]{8}$` alongside 3/6). On match: 8 digits → return `#` + first 6; 4 digits → return `#` + first 3; 3/6 digits unchanged. Preserve the existing resolution order (empty→None, `none`→`NONE`, `:`/`(` passthrough, hex, name, `ColorError`). Strip is silent (no stderr).
- [x] 1.2 Unit tests in `tests/unit/test_scenes_colors.py`: `#001f3faa`→`#001f3f`, `001f3faa`→`#001f3f` (hashless), `#f007`→`#f00`, `f007`→`#f00`, case-insensitive (`#001F3FAA`); confirm 5-char and 7-char tokens still raise `ColorError` (not valid hex lengths); confirm a 3/6 value is untouched.

## 2. Fill-current-tab only when solo (#2)

- [x] 2.1 Add `_origin_tab_is_solo(origin_window: int, to: str | None) -> bool` to `scenes/launcher.py`: run `_client.kitten_at("ls", to=to)`, `json.loads` stdout, find the tab whose `windows` contains a window with `id == origin_window`, return `len(windows) == 1`. Return `False` on any failure (non-zero ls, JSON error, origin id not found) — fail-safe.
- [x] 2.2 In `launch_scene`, change the in-kitty multi-pane guard from `if origin_window is not None and not single:` to also require `_origin_tab_is_solo(origin_window, to)`; otherwise fall through to the existing new-tab path. Update the docstring to state the solo condition + fail-safe.
- [x] 2.3 Unit test (`tests/unit/test_scenes_launcher.py`): monkeypatch `_client.kitten_at` to return a crafted `ls` JSON; assert `_origin_tab_is_solo` returns `True` for a 1-window tab, `False` for a 2-window tab, and `False` on a non-zero/garbage `ls` result.
- [x] 2.4 Integration test (`tests/integration/`, `KITTI_INTEGRATION=1`): spawn kitty, launch a 2nd window in the tab (now 2 windows), run a 3-pane scene from inside it → assert via `ls` that a NEW tab holds the 3 panes AND the original tab still has exactly 2 windows (not 4). Solo case: 1-window tab + 3-pane scene → 3 windows in the same tab, tab count unchanged.

## 3. Color name autocomplete (#1)

- [x] 3.1 Add `color_completer(prefix="", **_) -> list[str]` (in `scenes/colors.py`, beside `COLOR_NAMES`): return table keys starting with `prefix` EXCLUDING `grayN`/`greyN` numbered entries, plus `NONE`. Export via `scenes/__init__`.
- [x] 3.2 Wire `.completer = color_completer` in `cli.py` onto: the `<color>` positional of `tab accent`, the `<color>` positional of `window background`, and the `--tab-accent` option of `scene launch`. Mirror the `scene_name_completer` wiring (`cli.py:383`).
- [x] 3.3 Unit test: `color_completer(prefix="te")` includes `teal`; `prefix=""` includes `NONE` and `gray` but NOT `gray50`.

## 4. Seed example scenes on install (#3)

- [x] 4.1 `pyproject.toml`: force-include `examples/scenes` → `kitty_setup/_scenes` in the wheel (mirror the `config/kitty` → `kitty_setup/_payload/kitty` entry). Add a `_scenes_source()` resolver in `installer.py` mirroring `_payload_source()` (bundled path, repo fallback).
- [x] 4.2 Add `seed_scenes() -> tuple[int, int]` to `installer.py`: resolve the target via the recipe loader's `scenes_dir()`, `mkdir(parents=True, exist_ok=True)`, then for each bundled `*.toml` copy (`shutil.copy`) only if the target name is absent. Return `(seeded, kept)`. Call it from `install()` after config injection; print a one-line summary.
- [x] 4.3 Remove the `mkdir -p ~/.config/kitty-setup/scenes/` + `cp -r examples/scenes/*` lines from `tools/setup.sh` (logic moved to the subcommand).
- [x] 4.4 Confirm uninstall is unchanged (does NOT touch `~/.config/kitty-setup/scenes/`); add/adjust a unit test asserting `uninstall` leaves a sentinel scene file in place.
- [x] 4.5 Unit test for `seed_scenes` (monkeypatch `scenes_dir()` to a tmp path + a tmp bundled source): fresh dir → all examples seeded; pre-existing edited file → kept byte-for-byte, others added; idempotent on a second call (0 seeded).
- [x] 4.6 Update the example `*.toml` header comments — drop the manual `cp … ~/.config/...` instruction now that install seeds them.

## 5. Probe doc + verification

- [x] 5.1 Promote `tmp/h26-perpane-opacity/` into `docs/repro/h26-perpane-opacity.md` (Why, Manual repro, Linux Status on kitty 0.47.1 = opacity is OS-window scope only, macOS deferred-with-reason, Known limitations). Record both the per-pane and per-tab verdicts.
- [x] 5.2 `make format` / `ruff` / `pyright src` clean on changed + new files.
- [x] 5.3 Full `make test` green; `KITTI_INTEGRATION=1` integration green on host (capture the 4-window regression + seed-copy output for the handoff).
- [x] 5.4 `make doctor` clean (no regression; no new doctor check).
- [x] 5.5 `make install` re-run: confirm scenes are seeded copy-if-absent on a real run, and an edited recipe survives.
- [x] 5.6 `openspec validate phase2-scene-polish --strict` passes.
