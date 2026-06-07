"""Client-side color normalization for ``my-kitty`` (Phase 2 / friendly-color-input).

:func:`normalize_color` turns a user-supplied color into a value kitty always
accepts, BEFORE any ``kitten @`` call, so a bad color is rejected up front rather
than after a window/tab has already opened:

* empty string -> ``None`` (absent), matching ``parse_pane_spec`` / the recipe
  loader's empty-string handling.
* hex, with or WITHOUT a leading ``#``: ``#fff`` / ``fff`` / ``1a2b3c`` ->
  ``#...`` (the bare form a casual user types just works; kitty itself requires
  the ``#``). A 4- or 8-digit value carries an **alpha** channel (``#rgba`` /
  ``#rrggbbaa``); the alpha is **stripped** and the solid ``#rgb`` / ``#rrggbb``
  returned. kitty has no per-pane or per-tab opacity (probe-grounded against
  kitty 0.47.1: ``set-background-opacity`` is OS-window scope only — see
  ``docs/repro/h26-perpane-opacity.md``), so a color's alpha cannot become a
  per-pane translucency; opacity stays the explicit ``my-kitty os-window
  opacity`` gesture.
* a recognized X11/CSS color name -> its ``#rrggbb`` (see :mod:`._color_table`).
  The table is a superset of kitty's native names, so nothing that worked before
  breaks, and names kitty lacks (``teal``, ``olive``, ...) now resolve.
* the reset sentinel ``NONE`` and ``rgb:`` / functional ``rgb()`` forms pass
  through unchanged (kitty validates those).
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


class ColorError(ValueError):
    """Raised when a color value is neither valid hex nor a recognized name."""


def _strip_alpha(digits: str) -> str:
    """Return a solid ``#rgb``/``#rrggbb`` from 3/4/6/8 hex digits (alpha dropped).

    4-digit ``rgba`` -> ``#rgb`` (drop the last nibble); 8-digit ``rrggbbaa`` ->
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
    # Reset sentinel + functional/rgb: forms pass through for kitty to handle.
    if low == "none":
        return "NONE"
    if ":" in v or "(" in v:
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
