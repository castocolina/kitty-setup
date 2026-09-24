"""Client-side color normalization for ``my-kitty`` (Phase 2 / friendly-color-input).

:func:`normalize_color` turns a user-supplied color into a value kitty always
accepts, BEFORE any ``kitten @`` call, so a bad color is rejected up front rather
than after a window/tab has already opened:

* empty string -> ``None`` (absent), matching ``parse_pane_spec`` / the recipe
  loader's empty-string handling.
* hex, with or WITHOUT a leading ``#``: ``#fff`` / ``fff`` / ``1a2b3c`` ->
  ``#...`` (the bare form a casual user types just works; kitty itself requires
  the ``#``). A 4- or 8-digit value carries an **alpha** channel (a trailing
  alpha nibble or byte); the alpha is **stripped** and the solid ``#rgb`` /
  ``#rrggbb`` returned. kitty has no per-pane or per-tab opacity (probe-grounded
  against kitty 0.47.1: ``set-background-opacity`` is OS-window scope only — see
  ``docs/repro/h26-perpane-opacity.md``), so a color's alpha cannot become a
  per-pane translucency; opacity stays the explicit ``my-kitty os-window
  opacity`` gesture.
* a recognized X11/CSS color name -> its ``#rrggbb`` (see :mod:`._color_table`).
  The table is a superset of kitty's native names, so nothing that worked before
  breaks, and names kitty lacks (``teal``, ``olive``, ...) now resolve.
* the reset sentinel ``NONE`` passes through unchanged.
* ``rgb:<r>/<g>/<b>`` -- exactly three slash-separated groups of one to four hex
  digits, case-insensitive -- passes through unchanged. It is the ONLY colon or
  functional form kitty 0.49.0 accepts: measured at both ``kitten @ set-colors``
  and ``kitten @ set-tab-color``, every other one exits non-zero (the measured
  list lives beside the tests in ``tests/unit/test_scenes_colors.py``). It is
  matched whole (``fullmatch``), so a malformed ``rgb:`` is not passed on its
  prefix alone.
* anything else -> :class:`ColorError` (a ``ValueError``), so callers reject it
  before opening any window.

A 3-, 4-, 6-, or 8-character all-hex token is treated as hex; no X11/CSS color
name is an all-hex-digit string of those lengths, so the rule is unambiguous.
"""

from __future__ import annotations

import re

from kitty_setup.scenes._color_table import COLOR_NAMES

__all__ = ["ColorError", "color_completer", "normalize_color"]

# Numbered grays/greys (gray0..gray100, grey0..grey100) inflate the suggestion
# list with ~200 low-signal entries; they still RESOLVE via normalize_color, but
# are excluded from tab-completion. Matches `gray<digits>` / `grey<digits>`.
_NUMBERED_GRAY_RE = re.compile(r"gr[ae]y\d+")

# 3/6 = solid hex; 4/8 = hex + alpha (the alpha is stripped, see _strip_alpha).
_HEX_RE = re.compile(r"#?(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{4}|[0-9a-f]{3})")

# rgb:<r>/<g>/<b>, 1-4 hex digits per group: the one passthrough form kitty accepts.
# Measured on kitty 0.49.0's kitten: rgb:0/f/0 and rgb:00/ff/00 exit 0; a 4th group
# exits 1 and a 5-digit group panics it (tmp/h32-color-forms/). Matched on lower case.
_RGB_COLON_RE = re.compile(r"rgb:[0-9a-f]{1,4}/[0-9a-f]{1,4}/[0-9a-f]{1,4}")


class ColorError(ValueError):
    """Raised when a color value is neither valid hex nor a recognized name."""


def _strip_alpha(digits: str) -> str:
    """Return a solid ``#rgb``/``#rrggbb`` from 3/4/6/8 hex digits (alpha dropped).

    4 digits -> ``#rgb`` (drop the last, alpha, nibble); 8-digit ``rrggbbaa`` ->
    ``#rrggbb`` (drop the last byte); 3- and 6-digit values are returned as-is.
    """
    if len(digits) == 4:
        digits = digits[:3]
    elif len(digits) == 8:
        digits = digits[:6]
    return "#" + digits


def normalize_color(value: str | None) -> str | None:
    """Normalize a user color to a kitty-accepted string, or ``None`` if absent.

    Raises :class:`ColorError` on an unrecognized value so callers can reject it
    before any ``kitten @`` call.
    """
    if value is None:
        return None
    v = value.strip()
    if v == "":
        return None
    low = v.lower()
    # Reset sentinel and the one colon form kitty accepts pass through unchanged.
    if low == "none":
        return "NONE"
    if _RGB_COLON_RE.fullmatch(low):
        return v
    if _HEX_RE.fullmatch(low):
        return _strip_alpha(low.lstrip("#"))
    if low in COLOR_NAMES:
        return COLOR_NAMES[low]
    raise ColorError(
        f"{value!r} is not a recognized color — use a hex like '#0a7' / '0a7' "
        f"or a color name like 'teal'"
    )


def color_completer(*, prefix: str = "", **_kwargs: object) -> list[str]:
    """argcomplete completer for the ``<color>`` arguments.

    Returns color **names** from :data:`COLOR_NAMES` starting with ``prefix``,
    plus the reset sentinel ``NONE``, EXCLUDING the numbered ``grayN``/``greyN``
    entries (kept resolvable, just not suggested). Hex values are not
    enumerable and are not offered.
    """
    names = [
        name
        for name in COLOR_NAMES
        if name.startswith(prefix) and not _NUMBERED_GRAY_RE.fullmatch(name)
    ]
    if "NONE".startswith(prefix) or "none".startswith(prefix.lower()):
        names.append("NONE")
    return sorted(names)
