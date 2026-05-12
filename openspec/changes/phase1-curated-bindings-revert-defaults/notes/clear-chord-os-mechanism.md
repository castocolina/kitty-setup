# OS-conditional clear chord — implementation choice

## Context

design.md D5 binds the instant-clear chord to `super+k` on Linux and
`cmd+k` on macOS, with `ctrl+shift+alt+k` as a cross-OS fallback on both.
The spec also requires that every clear binding be reported under the
`clear` section by `my-kitty keys` (kitty-instant-clear scenario:
"the `clear` section lists at least two bindings"). The
`binding_introspection` module attributes a binding to a source by the
basename of the `.conf` file the `map` line was authored in, so both
bindings on a given OS must live in a file whose stem is `clear`.

## Approaches considered

### A) Single file, both lines authored

Put `map super+k …` and `map cmd+k …` into one `clear.conf`. **Rejected.**
Probe (manual, with `kitty +runpy` on 0.46.2 / Linux): kitty parses
`cmd+k` as an alias for `super+k`, so both lines collapse to a single
`super+k` entry — but with two definitions, causing the introspection
module to flag a conflict. Even if dedupe were tightened, the file
would still surface a misleading "cmd" identifier on Linux.

### B) Per-OS file split with `os` conditional include

`clear.conf` `include`s either `clear-linux.conf` or `clear-mac.conf`
via kitty's `os.platform`-conditional directive. **Rejected.** kitty
0.46.x has no documented per-OS conditional `include`; the closest is
the `--config` precedence, which still requires our code to pick the
file. So this collapses to (C) with extra ceremony.

### C) Two source files, installer renames the OS-matching one to `clear.conf`

**Chosen.** Ship `config/kitty/clear-linux.conf` and
`config/kitty/clear-mac.conf` in the repo; each is a complete `clear.conf`
for its OS, holding both the OS-native chord AND the `ctrl+shift+alt+k`
fallback. The installer (specifically `config_updater.install`) copies
the matching variant to `<payload_dir>/clear.conf` on the target host
after the `copytree` step, then removes the non-matching `clear-*.conf`
sibling. The deployed payload directory ends up with exactly one
`clear.conf`, whose source basename is `clear`, satisfying the
`my-kitty keys` "clear section" requirement on both OSes.

Test fixtures (`conftest.py::clear_conf`) read whichever source file
matches the current `sys.platform`, so the test suite is OS-aware too.

### D) Python templating from one `clear.conf.tmpl` file

Considered. Would work, but adds a template engine dependency for a
one-token swap and pulls more weight than the file-pick approach. **Rejected.**

## Mechanism — concrete steps

1. Repo carries `config/kitty/clear-linux.conf` and `config/kitty/clear-mac.conf`.
   Each file holds two `map` lines: the OS-native chord (`super+k` or
   `cmd+k`) plus `ctrl+shift+alt+k`.
2. The repo does NOT carry a literal `clear.conf` — the file is materialised
   from a variant at install time. Tests that need to read "the clear
   payload" read the right variant via a `sys.platform` switch in the
   conftest fixture.
3. `config_updater.install()` runs the existing `shutil.copytree`, then
   calls a new helper `_select_os_variants(payload_dir)` that:
   - Reads `sys.platform`. `"darwin"` → mac variant; everything else →
     Linux variant.
   - Renames `<payload_dir>/<variant>.conf` → `<payload_dir>/clear.conf`.
   - Removes the non-matching `clear-*.conf` sibling from the payload dir.
4. `kitty-setup.conf` keeps its existing `include clear.conf` line — the
   include resolves to the renamed file at runtime.
5. Uninstall is unaffected — the payload dir is deleted wholesale.

## Why this is the right call

* **Source attribution stays clean.** Both bindings live under source
  `clear` in `my-kitty keys`, satisfying the spec scenario.
* **No new dependency, no templating engine.** A four-line Python
  helper in the installer is all the OS pick needs.
* **Reversible.** Rolling back this change deletes both `clear-*.conf`
  files and restores the literal `clear.conf` from the archived prior
  change.
* **Test surface is symmetric across OSes.** A single
  `conftest.py::clear_conf` fixture maps to whichever variant the host
  needs.
