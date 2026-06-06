"""Client-side color normalization for ``my-kitty`` (Phase 2 / friendly-color-input).

:func:`normalize_color` turns a user-supplied color into a value kitty always
accepts, BEFORE any ``kitten @`` call, so a bad color is rejected up front rather
than after a window/tab has already opened:

* empty string -> ``None`` (absent), matching ``parse_pane_spec`` / the recipe
  loader's empty-string handling.
* hex, with or WITHOUT a leading ``#``: ``#fff`` / ``fff`` / ``1a2b3c`` ->
  ``#...`` (the bare form a casual user types just works; kitty itself requires
  the ``#``).
* a recognized X11/CSS color name -> its ``#rrggbb`` (see :mod:`._color_table`).
  The table is a superset of kitty's native names, so nothing that worked before
  breaks, and names kitty lacks (``teal``, ``olive``, ...) now resolve.
* the reset sentinel ``NONE`` and ``rgb:`` / functional ``rgb()`` forms pass
  through unchanged (kitty validates those).
* anything else -> :class:`ColorError` (a ``ValueError``), so callers reject it
  before opening any window.

A 3- or 6-character all-hex token is treated as hex; no X11/CSS color name is a
3- or 6-char all-hex-digit string, so the rule is unambiguous.
"""

from __future__ import annotations

import re

from kitty_setup.scenes._color_table import COLOR_NAMES

__all__ = ["ColorError", "normalize_color"]

_HEX_RE = re.compile(r"#?[0-9a-f]{3}(?:[0-9a-f]{3})?")


class ColorError(ValueError):
    """Raised when a color value is neither valid hex nor a recognized name."""


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
    # Reset sentinel + functional/rgb: forms pass through for kitty to handle.
    if low == "none":
        return "NONE"
    if ":" in v or "(" in v:
        return v
    if _HEX_RE.fullmatch(low):
        return low if low.startswith("#") else "#" + low
    if low in COLOR_NAMES:
        return COLOR_NAMES[low]
    raise ColorError(
        f"{value!r} is not a recognized color — use a hex like '#0a7' / '0a7' "
        f"or a color name like 'teal'"
    )
