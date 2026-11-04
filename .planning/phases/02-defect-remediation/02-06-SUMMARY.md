---
phase: 02-defect-remediation
plan: 06
subsystem: scenes
status: complete
tags: [R1.7, D-12, U-2, colors, scene-primitives, tdd]
requires: [02-05]
provides:
  - "`normalize_color` passes through only `rgb:<r>/<g>/<b>` (three groups of 1-4 hex digits, case-insensitive), matched by an anchored `_RGB_COLON_RE.fullmatch`. Every other colon or parenthesised form, including `rgba:`, `rgb()`, `rgba()`, `hsl()`, `foo:bar`, `a(b` and malformed `rgb:`, now raises `ColorError` before any kitten call"
  - "`set_window_background` makes no kitten call and returns 0 for an absent colour (`None`, empty or whitespace-only)"
  - "`set_tab_accent` leaves out the bg arguments for an absent colour and keeps the fg overrides. When nothing is left to set, it makes no kitten call and returns 0. The check runs on the assembled settings list"
  - "both primitives accept `color: str | None`"
affects: [02-08]
tech-stack:
  added: []
  patterns:
    - "a function that returns `T | None`, where `None` means absent, is branched on with `is None`. It is never rescued by truthiness (`f(x) or x`)"
    - "the accepted set of a passthrough is measured against the consumer, here the kitten at both verbs. It is not read from docs or from a laxer parser. `to_color` accepts `rgb:0/0/0/0` and `rgb:fffff/0/0`, but the kitten rejects the first and panics on the second"
key-files:
  created:
    - .planning/phases/02-defect-remediation/02-06-SUMMARY.md
  modified:
    - src/kitty_setup/scenes/colors.py
    - src/kitty_setup/scenes/background.py
    - src/kitty_setup/scenes/accent.py
    - tests/unit/test_scenes_colors.py
    - tests/unit/test_scenes_background.py
    - tests/unit/test_scenes_accent.py
    - tests/integration/test_color_normalization_e2e.py
decisions:
  - "The regex is `rgb:` plus exactly three groups of `{1,4}` hex digits. These bounds come from the kitten, not from `to_color`. The kitten exits 1 on a fourth group and panics (exit 2) on a five-digit group, while `to_color` accepts both. The kitten is what `normalize_color` feeds"
  - "A passthrough value is returned exactly as given (after `strip()`), so `RGB:00/FF/00` passes unchanged. The kitten accepts it (exit 0 at both verbs)"
  - "The `none`/`NONE` reset-sentinel path is pinned by guard tests and was not changed. It is the Phase 6 blocker recorded in `.planning/STATE.md`"
  - "Functional-form support (translating `rgb()`/`hsl()` to hex on the client) is deferred. It would be a new feature, not this defect fix"
metrics:
  duration: "~10 min"
  completed: 2026-09-24
actuals:
  tokens: 11000
  tasks: 2
  commits: 2
plan_head_before: 9d13c908827b4f03d06a31d68f44a2f42e73545e
---

# Phase 2 Plan 06: an absent colour is absent, and only `rgb:` passes through (summary)

Before this plan, a colour reached kitty in two broken ways. An empty colour was not treated as
absent. `normalize_color` returned `None`, and then `normalize_color(c) or c` in
`background.py:30` and `accent.py:32` turned that `None` back into the raw input. So `''` reached
the kitten as `background=`, and `None` reached it as the literal `background=None`. The kitten
failed with `Error:  is not a valid color`. Also, any value that contained a `:` or a `(` passed
through, and kitty 0.49.0 rejects every such form except `rgb:`.

Both defects are fixed. An absent colour now emits no kitten argument. Only an anchored `rgb:`
form passes through. The test that asserted `rgba(1,2,3,0.5)` passes through has been inverted
and renamed.

Scope anchor (pre-work `HEAD`): `9d13c908827b4f03d06a31d68f44a2f42e73545e` (`9d13c90`, tip of
`gsd/phase-02-defect-remediation`). The harness worktree started at `23aeaa1` and was reset to
the phase branch before any work, as instructed. `core.hooksPath` read
`/var/home/bazzite/git/personal/kitty-setup/tools/hooks` (absolute) just after the reset. About
a minute later it read `tools/hooks` (relative, `file:.git/config`), and it still does. This agent
did not change it. Another session probably re-ran `make hooks` in between. It is reported here
and was not touched.

## Commits

| Kind | SHA | Subject |
|------|-----|---------|
| RED | `1ed974f` | `test(02-06): RED — colour passthrough admits only rgb:, an absent colour makes no kitten call (R1.7)` |
| GREEN | (this commit) | `feat(02-06): GREEN — …` |

RED holds only the four test modules. GREEN holds `colors.py`, `background.py`, `accent.py` and
this SUMMARY, and no file under `tests/`. `launcher.py` is untouched.

## Step 0: h32 reproduction, before any test or source edit (`tmp/h32-color-forms/`)

`tmp/h32-color-forms/` was created first. It holds `repro.md`, `run.py` and `actual.json`, plus
`actual-{before,after}.json`, `run-before-nolive.txt`, `run-before.txt`, `run-after.txt`,
`live-matrix-{before,after}.json`, `digits.txt` and the gate scripts. kitty is 0.49.0 at
`~/.local/kitty.app/bin/kitty`. No window reached the desktop, and the user's live kitty was never
contacted. The evidence comes from three paths:

- **stub**: in process, with `_client.kitten_at` replaced by a recorder (`run.py`).
- **to_color**: kitty's own parser through `timeout 30 kitty +runpy`, which opens no window
  (`run.py`, `digits.sh`).
- **live**: `probe_live_test.py`, copied to `tests/integration/test_h32_live_probe.py` for one
  `make test-integration` run inside the headless cage runner, then deleted and never staged
  (`live.sh <label>`). `run.py` merges the newest `live-matrix-*.json` and says which path it
  took.

### Twelve-value matrix, live kitten, both verbs (`live-matrix-before.json`; `-after.json` is identical)

| value | `set-colors background=` | `set-tab-color active_bg=` | `to_color` | verdict |
|---|---|---|---|---|
| `#0a7` | exit 0 | exit 0 | accepted | hex, accepted |
| `red` | exit 0 | exit 0 | accepted | name, accepted |
| `teal` | exit 1 `teal is not a valid color` | exit 1 | rejected | kitty lacks the name; `normalize_color` maps it to `#008080` first |
| `rgb:00/ff/00` | **exit 0** | **exit 0** | accepted | passthrough, accepted |
| `rgb:0/f/0` | **exit 0** | **exit 0** | accepted | passthrough, accepted |
| `rgba:00/ff/00/80` | **exit 1** `… is not a valid color` | **exit 1** | rejected | now a `ColorError` |
| `rgb(1,2,3)` | **exit 1** | **exit 1** | rejected | now a `ColorError` |
| `rgba(1,2,3,0.5)` | **exit 1** | **exit 1** | rejected | now a `ColorError` |
| `hsl(120,50%,50%)` | **exit 1** | **exit 1** | rejected | now a `ColorError` |
| `foo:bar` | exit 1 | exit 1 | rejected | now a `ColorError` |
| `""` / `" "` | exit 1 `Error:  is not a valid color` | exit 1 | rejected | now **absent**: no argument |
| `NONE` / `none` | **exit 1** `The color background cannot be set to none` | **exit 0** | rejected | reset sentinel, pinned and unchanged (Phase 6) |

Extra rows from the same run: `RGB:00/FF/00` exits 0 at both verbs. `rgb:xyz/00/00`, `rgb:00/00`,
`a(b` and `rgb:0/0/0/0` exit 1 at both verbs. `rgb:fffff/0/0` exits **2 with a Go panic**
(`slice bounds out of range [:2] with length 1`, `style/wrapper.go:76`) at both verbs.

### `to_color` probe output (kitty 0.49.0, `kitty +runpy`, no window)

From `run.py`: of the 18 values it probes, `to_color` accepts exactly `#0a7`, `red`,
`rgb:00/ff/00`, `rgb:0/f/0` and `RGB:00/FF/00`. Every other value raises
`ValueError: Invalid color name: '<value>'`. That includes `teal`, `rgba:00/ff/00/80`,
`rgb(1,2,3)`, `rgba(1,2,3,0.5)`, `hsl(120,50%,50%)`, `foo:bar`, `''`, `' '`, `NONE`, `none`,
`a(b`, `rgb:xyz/00/00` and `rgb:00/00`. The bounds probe, `digits.txt`:

```
'rgb:ffff/ffff/ffff' ACCEPTED Color(255, 255, 255)
'rgb:fffff/0/0' ACCEPTED Color(255, 0, 0)
'rgb:/0/0' REJECTED ValueError Invalid color name: 'rgb:/0/0'
'rgb:0/0/0/0' ACCEPTED Color(0, 0, 0)
' rgb:0/0/0' ACCEPTED Color(0, 0, 0)
'Rgb:A/b/C' ACCEPTED Color(170, 187, 204)
```

`to_color` is laxer than the kitten. The regex bounds, three groups of `{1,4}` digits, therefore
come from the kitten rows above.

### `my-kitty window background ''`, real kitty (headless), before and after

| argv | before (`9d13c90` tree) | after (GREEN tree) |
|---|---|---|
| `my-kitty window background ''` | rc=1 `Error:  is not a valid color` | **rc=0, stderr empty** |
| `my-kitty window background '   '` | rc=1 `Error:     is not a valid color` | **rc=0, stderr empty** |
| `my-kitty tab accent ''` | rc=1 `Error:  is not a valid color` | **rc=0, stderr empty** |
| `my-kitty window background 'rgba(1,2,3,0.5)'` | rc=1 `Error: rgba(1,2,3,0.5) is not a valid color` (from the kitten) | rc=1 `my-kitty window background: 'rgba(1,2,3,0.5)' is not a recognized color — …` (from us, before any kitten call) |
| `my-kitty window background rgb:00/ff/00` | rc=0 | rc=0 |
| `my-kitty window background teal` | rc=0 | rc=0 |
| `my-kitty window background none` | rc=1 `Error: The color background cannot be set to none` | **same** (Phase 6 blocker, not touched) |
| `my-kitty tab accent none` | rc=0 | rc=0 |

The committed integration case `test_empty_colour_window_background_is_absent` passes on
GREEN. The empty colour exits 0, stderr is `""`, and the active window's `get-colors`
background is unchanged.

### `run.py` transcript, step 0 (before any edit), compacted by `digest.py` from `actual-before.json`

The first run (`run-before-nolive.txt`) happened before any live file existed and reported
`"live": {"taken": false, "why": "no headless live-matrix file yet; the user's live kitty is never
probed"}`. It was re-run once `live-matrix-before.json` existed, which gives:

```
== run.py before: normalize_color (stub path)
  '#0a7'                 -> '#0a7'
  'red'                  -> '#ff0000'
  'teal'                 -> '#008080'
  'rgb:00/ff/00'         -> 'rgb:00/ff/00'
  'rgb:0/f/0'            -> 'rgb:0/f/0'
  'rgba:00/ff/00/80'     -> 'rgba:00/ff/00/80'
  'rgb(1,2,3)'           -> 'rgb(1,2,3)'
  'rgba(1,2,3,0.5)'      -> 'rgba(1,2,3,0.5)'
  'hsl(120,50%,50%)'     -> 'hsl(120,50%,50%)'
  'foo:bar'              -> 'foo:bar'
  ''                     -> 'None'
  ' '                    -> 'None'
  'NONE'                 -> 'NONE'
  'none'                 -> 'NONE'
  'a(b'                  -> 'a(b'
  'rgb:xyz/00/00'        -> 'rgb:xyz/00/00'
  'rgb:00/00'            -> 'rgb:00/00'
  'RGB:00/FF/00'         -> 'RGB:00/FF/00'
== primitives (stub path, recorded kitten calls)
  set_window_background('')                                      rc/raise=0            calls=[['set-colors', 'background=']]
  set_window_background('   ')                                   rc/raise=0            calls=[['set-colors', 'background=   ']]
  set_window_background(None)                                    rc/raise=0            calls=[['set-colors', 'background=None']]
  set_window_background('#0a7')                                  rc/raise=0            calls=[['set-colors', 'background=#0a7']]
  set_window_background('none')                                  rc/raise=0            calls=[['set-colors', 'background=NONE']]
  set_window_background('rgba(1,2,3,0.5)')                       rc/raise=0            calls=[['set-colors', 'background=rgba(1,2,3,0.5)']]
  set_tab_accent('')                                             rc/raise=0            calls=[['set-tab-color', 'active_bg=', 'inactive_bg=']]
  set_tab_accent('', active_fg='white', inactive_fg='gray')      rc/raise=0            calls=[['set-tab-color', 'active_bg=', 'inactive_bg=', 'active_fg=#ffffff', 'inactive_fg=#bebebe']]
  set_tab_accent('#0a7')                                         rc/raise=0            calls=[['set-tab-color', 'active_bg=#0a7', 'inactive_bg=#0a7']]
  set_tab_accent('NONE')                                         rc/raise=0            calls=[['set-tab-color', 'active_bg=NONE', 'inactive_bg=NONE']]
  set_tab_accent('hsl(120,50%,50%)')                             rc/raise=0            calls=[['set-tab-color', 'active_bg=hsl(120,50%,50%)', 'inactive_bg=hsl(120,50%,50%)']]
== to_color path taken: True
  accepted: ['#0a7', 'red', 'rgb:00/ff/00', 'rgb:0/f/0', 'RGB:00/FF/00']
== live path taken: True (live-matrix-before.json)
  my-kitty window background ''  rc=1  stderr='Error:  is not a valid color'
  my-kitty window background '   '  rc=1  stderr='Error:     is not a valid color'
  my-kitty tab accent ''  rc=1  stderr='Error:  is not a valid color'
  my-kitty window background rgba(1,2,3,0.5)  rc=1  stderr='Error: rgba(1,2,3,0.5) is not a valid color'
  my-kitty window background rgb:00/ff/00  rc=0  stderr=''
  my-kitty window background teal  rc=0  stderr=''
  my-kitty window background none  rc=1  stderr='Error: The color background cannot be set to none'
  my-kitty tab accent none  rc=0  stderr=''
```

(The stub `rc=0` values above come from the recorder's fake success. The live rows show what the
kitten really returns.)

### `run.py` transcript, after the fixes (`actual-after.json`)

```
== run.py after: normalize_color (stub path)
  '#0a7'                 -> '#0a7'
  'red'                  -> '#ff0000'
  'teal'                 -> '#008080'
  'rgb:00/ff/00'         -> 'rgb:00/ff/00'
  'rgb:0/f/0'            -> 'rgb:0/f/0'
  'rgba:00/ff/00/80'     -> "ColorError: 'rgba:00/ff/00/80' is not a recognized color"
  'rgb(1,2,3)'           -> "ColorError: 'rgb(1,2,3)' is not a recognized color"
  'rgba(1,2,3,0.5)'      -> "ColorError: 'rgba(1,2,3,0.5)' is not a recognized color"
  'hsl(120,50%,50%)'     -> "ColorError: 'hsl(120,50%,50%)' is not a recognized color"
  'foo:bar'              -> "ColorError: 'foo:bar' is not a recognized color"
  ''                     -> 'None'
  ' '                    -> 'None'
  'NONE'                 -> 'NONE'
  'none'                 -> 'NONE'
  'a(b'                  -> "ColorError: 'a(b' is not a recognized color"
  'rgb:xyz/00/00'        -> "ColorError: 'rgb:xyz/00/00' is not a recognized color"
  'rgb:00/00'            -> "ColorError: 'rgb:00/00' is not a recognized color"
  'RGB:00/FF/00'         -> 'RGB:00/FF/00'
== primitives (stub path, recorded kitten calls)
  set_window_background('')                                      rc/raise=0            calls=[]
  set_window_background('   ')                                   rc/raise=0            calls=[]
  set_window_background(None)                                    rc/raise=0            calls=[]
  set_window_background('#0a7')                                  rc/raise=0            calls=[['set-colors', 'background=#0a7']]
  set_window_background('none')                                  rc/raise=0            calls=[['set-colors', 'background=NONE']]
  set_window_background('rgba(1,2,3,0.5)')                       rc/raise="ColorError: 'rgba(1,2,3,0.5)' is not a recognized color — …" calls=[]
  set_tab_accent('')                                             rc/raise=0            calls=[]
  set_tab_accent('', active_fg='white', inactive_fg='gray')      rc/raise=0            calls=[['set-tab-color', 'active_fg=#ffffff', 'inactive_fg=#bebebe']]
  set_tab_accent('#0a7')                                         rc/raise=0            calls=[['set-tab-color', 'active_bg=#0a7', 'inactive_bg=#0a7']]
  set_tab_accent('NONE')                                         rc/raise=0            calls=[['set-tab-color', 'active_bg=NONE', 'inactive_bg=NONE']]
  set_tab_accent('hsl(120,50%,50%)')                             rc/raise="ColorError: 'hsl(120,50%,50%)' is not a recognized color — …" calls=[]
== to_color path taken: True
  accepted: ['#0a7', 'red', 'rgb:00/ff/00', 'rgb:0/f/0', 'RGB:00/FF/00']
== live path taken: True (live-matrix-after.json)
  my-kitty window background ''  rc=0  stderr=''
  my-kitty window background '   '  rc=0  stderr=''
  my-kitty tab accent ''  rc=0  stderr=''
  my-kitty window background rgba(1,2,3,0.5)  rc=1  stderr="my-kitty window background: 'rgba(1,2,3,0.5)' is not a recognized color — use a hex like '#0a7' / '0a7' or a color name like 'teal'"
  my-kitty window background rgb:00/ff/00  rc=0  stderr=''
  my-kitty window background teal  rc=0  stderr=''
  my-kitty window background none  rc=1  stderr='Error: The color background cannot be set to none'
  my-kitty tab accent none  rc=0  stderr=''
```

## Argument lists for each absence case, before and after (recorded kitten calls)

| case | before | after |
|---|---|---|
| `set_window_background('')` | `set-colors background=` | **no call**, returns 0 |
| `set_window_background('   ')` | `set-colors background=   ` | **no call**, returns 0 |
| `set_window_background(None)` | `set-colors background=None` | **no call**, returns 0 |
| `set_tab_accent('')` | `set-tab-color active_bg= inactive_bg=` | **no call**, returns 0 |
| `set_tab_accent('', match='id:1')` | `set-tab-color --match id:1 active_bg= inactive_bg=` | **no call**, returns 0 |
| `set_tab_accent('', active_fg='white', inactive_fg='gray')` | `set-tab-color active_bg= inactive_bg= active_fg=#ffffff inactive_fg=#bebebe` | `set-tab-color active_fg=#ffffff inactive_fg=#bebebe` |
| `set_window_background('#0a7')` (guard) | `set-colors background=#0a7` | unchanged |
| `set_tab_accent('#0a7')` (guard) | `set-tab-color active_bg=#0a7 inactive_bg=#0a7` | unchanged |
| `none`/`NONE` (guard, both) | `background=NONE` / `active_bg=NONE inactive_bg=NONE` | unchanged |

## The inverted test, before and after

Before (`tests/unit/test_scenes_colors.py:122-124` at `9d13c90`):

```python
def test_functional_and_rgb_forms_pass_through() -> None:
    assert normalize_color("rgb:00/ff/00") == "rgb:00/ff/00"
    assert normalize_color("rgba(1,2,3,0.5)") == "rgba(1,2,3,0.5)"
```

After (RED commit onward):

```python
def test_passthrough_rejects_rgba_function_but_keeps_rgb_colon() -> None:
    # Inverted by 02-06 (D-12 as amended by U-2). … kitty 0.49.0 rejects it at both
    # kitten verbs …, so the only passthrough form is `rgb:`.
    assert normalize_color("rgb:00/ff/00") == "rgb:00/ff/00"
    with pytest.raises(ColorError):
        normalize_color("rgba(1,2,3,0.5)")
```

The new name says what the test asserts. `rgba()` is rejected, and the surviving `rgb:` assertion
from `:123` still passes.

## The docstring corrections

- `colors.py` module docstring, before: *"the reset sentinel ``NONE`` and ``rgb:`` / functional
  ``rgb()`` forms pass through unchanged (kitty validates those)."* After: two bullets. The first
  says the reset sentinel passes through unchanged. The second says ``rgb:<r>/<g>/<b>`` (exactly
  three groups of one to four hex digits, case-insensitive) *"is the ONLY colon or functional form
  kitty 0.49.0 accepts: measured at both ``kitten @ set-colors`` and ``kitten @ set-tab-color``,
  every other one exits non-zero … It is matched whole (``fullmatch``), so a malformed ``rgb:``
  is not passed on its prefix alone."* The names of the rejected forms were moved into the case
  comments of `tests/unit/test_scenes_colors.py`, as the plan allows for gate g02.
- `background.py` `set_window_background` gained: *"An absent color (``None``, empty or
  whitespace-only) sets nothing: no kitten call is made and 0 is returned."*
- `accent.py` `set_tab_accent` gained: *"An absent value (``None``, empty or whitespace-only)
  emits no argument: an absent color omits ``active_bg``/``inactive_bg`` but keeps the fg
  overrides, and when nothing at all is left to set no kitten call is made and 0 is returned."*
- The inline comment at `colors.py:76`, *"Reset sentinel + functional/rgb: forms pass through for
  kitty to handle"*, was corrected to match.

## RED state, proven from the RED commit's own tree

Gate g13 materialises `1ed974f` through a throwaway index and runs the unit defect selector with
the RED tree's `src` on `PYTHONPATH`. Pytest status is 1: **18 failed, 67 deselected**, and none
passed or errored (the floor is 14). Gate status is 0, with `N=18`. Transcript
`tmp/h32-color-forms/g13-transcript.txt`:

```
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_rgba_function_but_keeps_rgb_colon
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_kitty_rejected_form[rgba:00/ff/00/80]
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_kitty_rejected_form[rgb(1,2,3)]
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_kitty_rejected_form[rgba(1,2,3,0.5)]
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_kitty_rejected_form[hsl(120,50%,50%)]
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_junk[foo:bar]
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_junk[a(b]
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_malformed_rgb_colon[rgb:xyz/00/00]
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_malformed_rgb_colon[rgb:00/00]
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_malformed_rgb_colon[rgb:0/0/0/0]
FAILED tests/unit/test_scenes_colors.py::test_passthrough_rejects_malformed_rgb_colon[rgb:fffff/0/0]
FAILED tests/unit/test_scenes_background.py::test_set_window_background_absent_no_call[empty]
FAILED tests/unit/test_scenes_background.py::test_set_window_background_absent_no_call[whitespace]
FAILED tests/unit/test_scenes_background.py::test_set_window_background_absent_no_call[none-object]
FAILED tests/unit/test_scenes_accent.py::test_set_tab_accent_absent_no_call[empty]
FAILED tests/unit/test_scenes_accent.py::test_set_tab_accent_absent_no_call[whitespace]
FAILED tests/unit/test_scenes_accent.py::test_set_tab_accent_absent_no_call_with_match_only
FAILED tests/unit/test_scenes_accent.py::test_set_tab_accent_absent_keeps_fg
18 failed, 67 deselected in 0.09s
--- gate status: 0; N=18 ---
```

Gate g14 runs `make test-integration PYTEST_ARGS='… -k empty_colour'` from the same materialised
tree, with `UV_NO_SYNC=1` and the venv pinned. It passes (exit 0, `N=1`). Transcript
`g14-transcript.txt`:

```
E           AssertionError: Error:  is not a valid color
E           assert 1 == 0
tests/integration/test_color_normalization_e2e.py:114: AssertionError
FAILED tests/integration/test_color_normalization_e2e.py::test_empty_colour_window_background_is_absent
1 failed, 3 deselected in 0.73s
test-integration: pytest exit status 1 (read from the child's status file; compositor exited 1)
make: *** [Makefile:40: test-integration] Error 1
--- gate status: 0; N=1 ---
```

The guard cases are `test_guard_rgb_colon_forms_pass` (×3), `test_guard_hex_unchanged` (one in
each primitive module) and `test_guard_none_sentinel` (×2 in each). They fall outside the
selectors and pass at RED: the complementary selector gave `67 passed, 18 deselected` on the RED
working tree (`redcheck-worktree.txt`).

## Stated facts (recorded, not changed)

- **`my-kitty window background none` is a Phase 6 blocker. It was pinned, not fixed.** Kitty
  0.49.0 rejects `set-colors background=NONE` (exit 1 `The color background cannot be set to
  none`) and accepts `set-tab-color active_bg=NONE` (exit 0). This was measured again here, before
  and after the change. `.planning/STATE.md:78` records it as the `[Phase 6]` blocker for R4.1:
  the `none` slot has to reset **both** colours. This plan changed nothing on that path.
  `normalize_color('none')` still returns `NONE`, and both primitives still send it to the kitten.
  The `test_guard_none_sentinel` cases in `test_scenes_background.py` and `test_scenes_accent.py`
  record the starting point Phase 6 inherits.
- **Deferred idea: support for functional forms.** Translating `rgb(1,2,3)`, `rgba(…)` or
  `hsl(…)` to hex on the client would be a reasonable feature. Kitty rejects all three, so
  accepting them means *adding* a new input grammar with its own parsing, clamping and alpha
  rules. It is not the fix for D-12's defect, which is that a form kitty rejects must be rejected
  here first. It was not implemented, and the regex was not widened "just in case". Any future
  phase that wants it should plan it as a feature.
- **`launcher.py` is untouched**, as gate g08 (working tree) and gate g15 (GREEN commit) confirm.
  Its colour path was already correct: `_apply_bg` returns early on `None`.
- **Seeded scenes are unaffected.** All four `examples/scenes/*.toml` use hex or names. `make test`
  (below) includes the scene tests and passes.

## Gates

Every `<automated>` gate was extracted verbatim from `02-06-PLAN.md` (HTML-unescaped) into
`tmp/h32-color-forms/gates/gNN.sh` by `extract_gates.py`, with only a `cd <worktree>` line
added. The `<verification>` commands 1-8 were extracted the same way (`extract_vgates.py` →
`vNN.sh`). `rungates.py` logs each exit status to `gates.log`. For g09, g10, g13 and g14,
`showgate.py` added a trailer that prints `$OUT` and the gate's status and leaves the gate text
unchanged. **No gate was changed.**

| # | Gate | When run | Exit |
|---|------|----------|------|
| g01 | T1: `rgb:` + `fullmatch` in `colors.py`, no broad contains-test | pre-work: 1 (expected); after fix | **0** |
| g02 | T1: no `rgba\|hsl` in `colors.py` | pre-work: 1; after fix | **0** |
| g03 | T1: `test_scenes_colors.py` all green | after fix | **0** |
| g04 | T1: `tmp/h32-color-forms/{repro.md,run.py,actual.json}` exist | pre-work (step 0 done): 0; after fix | **0** |
| g05 | T1: old test name gone | pre-work: 1; after RED | **0** |
| g06 | T2: `is None` in both primitives, no `normalize_color(color) or color` | pre-work: 1; after fix | **0** |
| g07 | T2: background + accent modules green | after fix | **0** |
| g08 | T2: `launcher.py` untouched (worktree + index) | before GREEN commit | **0** |
| g09 | T2: `make test-integration` on `test_color_normalization_e2e.py`: passed, no fail | after fix | **0** (4 passed) |
| g10 | T2: `make test` ≥ 314 passed, no fail/error | after fix | **0** (449 passed) |
| g11 | topology: one `test(02-06)`, one `feat(02-06)`, RED ancestor of GREEN, exactly two `(02-06)` from RED^ | after GREEN | see below |
| g12 | RED is tests-only and holds all four modules | after RED | **0** |
| g13 | RED tree, unit: status 1, ≥14 failed, none passed/errored | after RED | **0** (18 failed) |
| g14 | RED tree, integration `empty_colour`: non-zero, runner reports pytest status 1, ≥1 failed, none passed/skipped/errored | after RED | **0** (1 failed) |
| g15 | GREEN contains the SUMMARY, not `launcher.py` | after GREEN | see below |
| g16 | GREEN holds no `tests/` path | after GREEN | see below |
| v01-v05 | verification items 1-5 | after fix | **0** each |
| v06 | verification item 6 (integration e2e module) | after fix | **0** |
| v07 | verification item 7 (`make test` floor) | after fix | **0** |
| v08 | `ruff check` + `black --check` on the three source files | after fix | **0** |

The commit-dependent gates g11, g12, g15 and g16 are run after the GREEN commit. Their results
are recorded in "Post-commit gate results" below.

## Baselines and lint

`make test`: exit 0, `======================= 449 passed, 78 skipped in 8.51s ========================`.
That is 423 at 02-05's GREEN (`9d13c90` adds only docs), plus the 26 unit items this plan adds:
17 new defect items and 9 guards. The 18th defect item is the renamed test, which was already
counted. The one new integration item is skipped under `make test`, which
takes skipped from 77 to 78. The floor is 314.

Integration (`make test-integration PYTEST_ARGS='tests/integration/test_color_normalization_e2e.py
-q'`, headless cage): `4 passed in 4.11s`, and the runner reported `pytest exit status 0`. No
`$XDG_RUNTIME_DIR/kitti-*` directory and no `cage` process was left after any run.

Repo-wide counts come from `tmp/h32-color-forms/lintcounts.py`, using the same venv tools on both
trees. `9d13c90` was materialised through a throwaway index:

| Tool | `9d13c90` | after | delta |
|------|-----------|-------|-------|
| `ruff check .` findings | 25 | 25 | 0 |
| `black --check .` files to reformat | 10 | 10 | 0 |
| `bandit -c pyproject.toml -r src` issues | 33 | 33 | 0 |
| `pyright` errors | 559 | 559 | 0 |
| `vulture src tests` lines | 15 | 15 | 0 |

Per touched file (`pyright_perfile.py`, a repo-wide pyright with the project config, counted by
file): `colors.py` 0→0, `background.py` 0→0, `accent.py` 0→0, `test_scenes_colors.py` 4→4,
`test_scenes_background.py` 3→3, `test_scenes_accent.py` 3→3,
`test_color_normalization_e2e.py` 9→9. All remaining findings are pre-existing: `_client`
private use, lambda stubs and `ls()` typing. ruff and black are clean on all seven touched files.
bandit is clean on the three source files. vulture reports nothing for them, and there is no
suppression comment in any of them.

## Deviations from Plan

**1. [Rule 2 - broader RED set] 18 defect cases rather than the planned 14.** The live probe
found two more malformed `rgb:` values that the kitten rejects: `rgb:0/0/0/0` (exit 1) and
`rgb:fffff/0/0` (exit 2, a Go panic). Both are now `passthrough_rejects` cases, and they are what
pins the regex's three groups and `{1,4}` bounds. The accent absence case covers `"   "` as well
as `""`. A `--match`-only case proves that the "nothing left to set" test ignores the selector.
All 18 fail at RED, and the plan's `≥ 14` floor is a floor. No gate was changed.

**2. [Rule 3 - typing] `color: str | None` in both primitives.** The planned
`set_background(None)` case needs `None` to type-check. At RED the pyright count rose by one
(`test_scenes_background.py:83`, `str | None` → `str`). The widened signature in GREEN brings it
back to 559. The CLI always passes a string, so behaviour is unchanged.

**3. [Gate-compatible rewording, not a gate change] Two hex-alpha phrasings in `colors.py` were
reworded.** Gate g02 (`rg -c 'rgba|hsl'`) also matched the hex-digit placeholder `#rgba` (module
docstring, `:11`) and "4-digit ``rgba``" (`_strip_alpha`, `:54`). Neither refers to the rejected
`rgba:`/`rgba()` form. They now read "a trailing alpha nibble or byte" and "4 digits -> ``#rgb``
(drop the last, alpha, nibble)". The meaning is the same and the gate is unchanged. The rejected
form names are in the test comments instead, as the plan allows.

**4. [Rule 3 - typing] The integration case reads the active window's colours without `--match`.**
`ls()` returns an untyped `list[dict]`, so `win = ls(...)[...]["id"]`, the sibling tests'
pattern, would add one pyright error. The scratch kitty has a single window, so the unmatched
`get-colors` and the command address the same window. The case still goes through `_run`, which
runs `sys.executable -m kitty_setup.cli`.

**5. [Method] The live matrix came from a temporary integration probe.** The runner rejects
paths outside `tests/integration`. `live.sh` therefore copied `probe_live_test.py` into
`tests/integration/test_h32_live_probe.py` for each run and deleted it afterwards (the script
checks this). It was never staged. Both commits list only the planned paths.

**6. [Method] Gate execution.** This agent's shell guard refuses compound one-liners that
mention `git`, or that `rtk` rewrites into `git`. The gates therefore ran from extracted script
files, as in 02-05. No gate was defective, so `02-06-PLAN.md` and `02-VALIDATION.md` were not
edited.

## Known limits and notes

- `docs/repro/friendly-color-input.md:25` and `:101` still describe the old `rgb()` / `rgba()`
  passthrough. The file is not in this plan's `files_modified`, so it is left for a
  docs-alignment pass. 02-08, which re-reads `tmp/h32-color-forms/`, is the natural owner.
- The `ColorError` message still suggests only hex and names. It does not mention `rgb:`. The
  message is unchanged by design (the plan changes no branch other than the passthrough).

## Known Stubs

None.

## Threat Flags

None new. T-2-21 is mitigated: the allow-list is narrowed to the measured accepted set. T-2-22 is
mitigated: explicit `is None` branches, with recorded-call tests. T-2-23 is mitigated: a rejected
form now fails before any kitten call. T-2-24 is mitigated: `fullmatch`, with four malformed-value
cases. T-2-SC: no package was installed.

## Post-commit gate results

These gates ran against the first GREEN commit, `e3f685d` (`gates.log`, "# after GREEN
e3f685d"). All exited **0**: g11 (topology), g12 (RED is tests-only and holds all four
modules), g13 (RED tree unit, 18 failed), g14 (RED tree integration, 1 failed), g15 (GREEN holds
the SUMMARY and not `launcher.py`), g16 (GREEN holds no `tests/` path), and the re-runs of g01,
g02, g05 and g06. For `e3f685d`, `git diff-tree` lists exactly `A
.planning/phases/02-defect-remediation/02-06-SUMMARY.md`, `M src/kitty_setup/scenes/accent.py`,
`M …/background.py` and `M …/colors.py`. The commit contains no deletions. GREEN was then amended
once while unpushed, to record this section and the Self-Check, and that amend changes only this
file. The commit-dependent gates were re-run on the amended SHA (see the Self-Check).
`git rev-list --count 9d13c90..HEAD` = 2.

## Self-Check: PASSED

- Found: the SUMMARY, the three source files, the four test modules, and
  `tmp/h32-color-forms/{repro.md,run.py,actual.json}`.
- Found commits: `1ed974f` (RED) and the GREEN commit.
- The temporary live-probe copy `tests/integration/test_h32_live_probe.py` is absent. No
  `$XDG_RUNTIME_DIR/kitti-*` directory and no `cage` process is left.
