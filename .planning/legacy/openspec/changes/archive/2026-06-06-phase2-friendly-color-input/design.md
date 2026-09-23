## Context

Color values reach kitty through four CLI surfaces, all passing the string raw
to `kitten @`:

```
my-kitty tab accent <color>          -> set-tab-color active_bg=<color> inactive_bg=<color>   (accent.py)
my-kitty window background <color>   -> set-colors background=<color>                          (background.py)
scene --pane 'bg=<color>'            -> set-colors background=<color>                          (launcher.py)
scene --tab-accent=<color>           -> set-tab-color ...                                       (launcher.py)
<name>.toml  bg= / tab_accent=       -> (same, via recipe.load_scene -> launch_scene)          (recipe.py)
```

The `phase2-scene-styling` spec deliberately forbade client-side validation
("MUST NOT validate ... rejected by kitten"). Empirically verified against
kitty 0.47.1 on the user's host:

| input | kitty result | want |
|---|---|---|
| `#fff` / `#000` / `#abc` | OK (`#aabbcc` expansion) | keep |
| `fff` / `000` / `ffffff` (no `#`) | **rejected** | accept → add `#` |
| `yellow` `blue` `navy` `orange` `gray50` `grey` | OK | keep |
| `teal` `olive` `lime` `aqua` `indigo` `crimson` | **rejected** | accept → translate to hex |
| `notacolor` | rejected | reject **before** opening any window |

X11-vs-CSS hex divergence exists for `green` (#00ff00 vs #008000), `gray`
(#bebebe vs #808080), `purple` (#a020f0 vs #800080), `maroon` (#b03060 vs
#800000). kitty uses the **X11** values (`gray` reads back `#bebebe`).

## Goals / Non-Goals

**Goals:**
- One shared `normalize_color(value) -> str` used by all five color sites.
- Accept hashless hex (`fff`, `1a2b3c`) — the casual-user friendliness ask.
- Accept the full X11/CSS named set; translate names kitty lacks to hex.
- **No tone change** for names kitty already renders (collision-free by design).
- Reject an unknown color **client-side, before any `kitten @ launch`**, so a
  scene never half-builds.
- Zero new dependencies; deterministic (no new wire probe).

**Non-Goals:**
- `NONE`/reset sentinels and `rgb:`/`rgba()` functional forms — passthrough as-is
  (kitty handles them); not part of v1 friendliness.
- Knowing kitty's *exact* internal table. We don't need it (see D2).
- Foreground/theme colors beyond the four listed commands' existing flags.

## Decisions

### D1 — Source the name→hex table from X11 `rgb.txt`, not CSS4

"X11" here names a **color-name database** (the data file `/usr/share/X11/rgb.txt`),
NOT the X11 display server — the table is windowing-system- and OS-independent
(Wayland / X11 / macOS all render a `#rrggbb` identically, and kitty's color
parser is the same cross-platform code everywhere).

The table is built **X11 `rgb.txt` first (precedence), then CSS/SVG fills only
the names X11 lacks**:
- kitty's own named-color table descends from X11 `rgb.txt`, so for every name
  kitty already accepts the X11 hex is *identical* to what kitty produces —
  `green` stays `#00ff00`, `gray` stays `#bebebe`, `purple` `#a020f0`, `maroon`
  `#b03060`. The X11-vs-CSS collision is avoided **by construction**: for a
  colliding name X11 wins, so we never emit the CSS value.
- The classic X11 `rgb.txt` predates the SVG/CSS additions, so it is **missing**
  exactly the names kitty also rejects — `teal`, `olive`, `lime`, `aqua`,
  `silver`, `fuchsia`, `indigo`, `crimson`. Those are added from the CSS3/SVG set
  (PIL `ImageColor.colormap`, generation-time only) **only when absent from
  X11**, plus `rebeccapurple` (#663399, a CSS4 addition in neither). Verified on
  the host: X11 base 658 + 9 CSS gap fills = **667** entries (incl. `grayN`/
  `greyN` 0–100, both spellings).

PIL is used **only at generation time**; the shipped `_color_table.py` is a pure
dict literal with no third-party import.

This also means "translate uniformly to hex" (the user's *"traslado uniforme"*)
and "do nothing for names kitty knows" (*"si kitty ya lo define, no hacemos
nada"*) are the **same operation** here — uniform translation whose result for
known names is visually a no-op.

### D2 — `normalize_color` resolution order

```
normalize_color(value: str) -> str            # raises ColorError
  v = value.strip()
  if v == "":            return None-equivalent (caller treats as absent)
  v = v.lower()
  if re.fullmatch(r"#?[0-9a-f]{3}", v) or re.fullmatch(r"#?[0-9a-f]{6}", v):
        return v if v.startswith("#") else "#" + v          # hashless hex friendliness
  if v in TABLE:         return TABLE[v]                     # name -> X11 hex (covers known + gap)
  raise ColorError(f"{value!r} is not a recognized color — "
                   f"use a hex like '#0a7' / '0a7' or a name like 'teal'")
```

We do **not** ask kitty to validate (no per-color `kitten @` round-trip). The
baked table is a verified **superset** of kitty's native names (task 1.3
enumerates kitty's accepted names and asserts `kitty_names ⊆ TABLE`), so any
name kitty would accept, `my-kitty` also accepts — nothing that worked before
breaks. Anything not in the table is genuinely unknown → reject.

### D3 — Pre-validate the whole scene before the first launch (atomicity)

The user's hard requirement: *"si no hace match … se rechace antes de intentar
abrir ningún window."* So normalization happens at the **front door**, not lazily
per pane:

- `recipe.load_scene` normalizes `bg`/`tab_accent` while building Panes; a bad
  value raises `SceneRecipeError` (no launch attempted at all).
- For the inline form, `cli_scene_launch` normalizes every `--pane bg` and
  `--tab-accent` **before** calling `launch_scene`; first bad value → exit 1, no
  `kitten @ launch`.
- The single-noun commands (`tab accent`, `window background`) normalize their
  argument before the single kitten call (there is no window to half-build, but
  the same code path and error surface apply for consistency).

Net: a scene with one bad color opens **zero** windows/tabs.

### D4 — `colors.py` owns it; the four sites import, never re-implement

Mirrors the `feedback_compose_reuse_primitive_argv` lesson: one normalizer, one
table, imported by `recipe.py` / `launcher.py` / `accent.py` / `background.py`.
`Pane.bg` stays a plain `str` (already-normalized hex or passthrough); no schema
change. The recipe loader normalizes *before* constructing the frozen `Pane`.

### D5 — Error type and message

`class ColorError(ValueError)` in `colors.py`. Callers map it to their existing
error surface: `parse_pane_spec`/inline → the `ValueError` path already prints to
stderr + exit 1; `recipe` wraps it as `SceneRecipeError`; `accent`/`background`
print to stderr + exit 1. Message names the offending value and shows both a hex
and a name example (friendly, actionable).

### D6 — Where the table literal lives

A generated `src/kitty_setup/scenes/_color_table.py` holding
`COLOR_NAMES: dict[str, str]` (name→`#rrggbb`), produced once from X11 `rgb.txt`
(+ `rebeccapurple`) and committed. A top-of-file comment records provenance and
the generating command. `colors.py` imports it. Keeping the data in its own
module keeps `colors.py` logic-only and reviewable.

## Risks / Trade-offs

- **Table drift vs kitty's table across versions.** Mitigation: task 1.3
  enumerates kitty's accepted names on the host and asserts subset; if a future
  kitty adds a name we lack, it still works (passthrough? no — we'd reject).
  Accepted: re-run the enumeration if kitty changes its table; the test catches
  it. Low risk (X11 set is stable).
- **Ambiguity: is a 3/6-char token hex or a name?** No X11/CSS name is a 3- or
  6-char all-hex-digit string, so `^#?[0-9a-f]{3,6}$` is unambiguous. Documented
  in `colors.py`.
- **Reversing a shipped requirement.** The `phase2-scene-styling` "MUST NOT
  validate client-side" clause is explicitly replaced; the proposal calls this
  out so the spec history is honest, not silently drifted.
- **`rgb:`/`rgba()` not normalized.** A user passing those still depends on
  kitty accepting them (passthrough). Acceptable for v1; noted as a known
  limitation in the repro doc.
- **Table size.** ~660 entries is a large literal, but static, generated, and
  zero-dep — the explicit project preference over adding a color library.
