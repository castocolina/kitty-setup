"""Scene composition primitive: launch a new tab with N pre-styled panes.

Phase 2 §12 of docs/requirements.md. First composition primitive on top of the
single-noun primitives (title, accent, background, font, opacity). Materialises
a new tab + chosen layout + N panes in one user gesture.

The kitten call algorithm is probe-grounded against ``tmp/h25-scene-launcher/``
(green on the user's host): launch + first-pane bg + goto-layout + per-pane
launch/bg + tab accent — 6 calls / ~85 ms for a 3-pane scene.

This module composes via raw ``_client.kitten_at()`` calls; it deliberately does
NOT import the per-primitive Python wrappers (title.py / accent.py / etc.) to
keep the dependency surface tight (one client wrapper) and to make the kitten
argv composition explicit and probe-traceable here.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from kitty_setup.scenes import _client
from kitty_setup.scenes._client import SceneClientError

_RECOGNISED_KEYS: tuple[str, ...] = ("title", "cmd", "cwd", "bg")


@dataclass(frozen=True)
class Pane:
    """A single pane spec parsed from one ``--pane key=value,...`` group.

    All four fields default to ``None``. ``None`` means "absent" and the
    corresponding kitten flag is omitted; a non-empty ``str`` means "present"
    and the flag is emitted. An empty user value (e.g. ``title=``) is
    normalised to ``None`` by :func:`parse_pane_spec`, never stored as ``""``.
    """

    title: str | None = None
    cmd: str | None = None
    cwd: str | None = None
    bg: str | None = None


def parse_pane_spec(s: str) -> Pane:
    """Parse a single ``--pane`` argument into a :class:`Pane`.

    Hand-written state machine (NOT shlex / csv). Recognises ``\\,`` as a
    literal comma and ``\\\\`` as a literal backslash; any other backslash
    sequence is preserved verbatim. Splits each comma-separated segment on
    the FIRST ``=`` only, so the value may contain ``=`` (e.g.
    ``cmd=docker run --env VAR=value bash``).

    Raises :class:`ValueError` on: empty input, segment with no ``=``,
    duplicate key, unknown key, leading/trailing/consecutive comma (empty
    segment).
    """
    if not s:
        raise ValueError("empty pane spec; expected at least one key=value")

    segments: list[str] = []
    buf: list[str] = []
    escape = False
    for ch in s:
        if escape:
            if ch in (",", "\\"):
                buf.append(ch)
            else:
                buf.append("\\")
                buf.append(ch)
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == ",":
            segments.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if escape:
        buf.append("\\")
    segments.append("".join(buf))

    fields: dict[str, str | None] = {}
    for seg in segments:
        if seg == "":
            raise ValueError(
                "trailing or leading comma in pane spec (empty segment); "
                "use \\, to escape a literal comma inside a value"
            )
        if "=" not in seg:
            raise ValueError(
                f"malformed pane spec; expected key=value, got '{seg}'"
            )
        key, _, value = seg.partition("=")
        if key not in _RECOGNISED_KEYS:
            raise ValueError(
                f"unknown key '{key}' in pane spec; "
                f"recognised keys: {', '.join(_RECOGNISED_KEYS)}"
            )
        if key in fields:
            raise ValueError(f"duplicate key '{key}' in pane spec")
        fields[key] = value if value != "" else None

    return Pane(
        title=fields.get("title"),
        cmd=fields.get("cmd"),
        cwd=fields.get("cwd"),
        bg=fields.get("bg"),
    )


def _launch_argv(
    pane: Pane,
    *,
    is_tab: bool,
    tab_title: str | None,
) -> list[str]:
    """Build the argv tail for one ``kitten @ launch`` call (kitten verb omitted)."""
    args: list[str] = ["--type=tab" if is_tab else "--type=window", "--hold"]
    if is_tab and tab_title is not None:
        args.append(f"--tab-title={tab_title}")
    if pane.title is not None:
        args.append(f"--title={pane.title}")
    if pane.cwd is not None:
        args.append(f"--cwd={pane.cwd}")
    if pane.cmd is not None:
        args.extend(["bash", "-lc", pane.cmd])
    return args


def launch_scene(
    layout: str | None,
    tab_title: str | None,
    tab_accent: str | None,
    panes: list[Pane],
    *,
    to: str | None = None,
) -> int:
    """Materialise a scene on the running kitty; return the first non-zero exit.

    Follows the probe-grounded kitten call algorithm (``design.md`` D3):

    1. ``launch --type=tab --hold`` combining tab-title, first-pane title /
       cwd / cmd in one call. Window id is captured from stdout.
    2. If the first pane has ``bg``: ``set-colors --match id:<win0>``.
    3. If ``layout`` is set: ``goto-layout <layout>``.
    4. For each remaining pane: ``launch --type=window --hold`` then
       ``set-colors --match id:<win>`` if ``bg``.
    5. If ``tab_accent`` is set: ``set-tab-color --match recent:0
       active_bg=<color> inactive_bg=<color>`` (mirrors :mod:`.accent`'s
       focused-AND-unfocused invariant; ``active`` alone is not a valid
       ``set-tab-color`` key).

    Fail-hard on ``launch`` non-zero (propagate exit code, stop processing).
    Fail-soft on ``set-colors`` and ``set-tab-color`` (print stderr, record
    the exit code, continue). Returns the first non-zero exit code, or ``0``
    if all calls succeed.

    Raises :class:`SceneClientError` (from :mod:`._client`) on socket discovery
    failures; callers should catch and surface via ``cli_scene_launch``.
    """
    if not panes:
        raise ValueError("launch_scene requires at least one Pane")

    first_error: int = 0

    p0 = panes[0]
    result = _client.kitten_at(
        "launch", *_launch_argv(p0, is_tab=True, tab_title=tab_title), to=to
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    win0 = int(result.stdout.strip())

    if p0.bg is not None:
        bg_result = _client.kitten_at(
            "set-colors",
            "--match",
            f"id:{win0}",
            f"background={p0.bg}",
            to=to,
        )
        if bg_result.returncode != 0:
            sys.stderr.write(bg_result.stderr)
            if first_error == 0:
                first_error = bg_result.returncode

    if layout is not None:
        layout_result = _client.kitten_at("goto-layout", layout, to=to)
        if layout_result.returncode != 0:
            sys.stderr.write(layout_result.stderr)
            if first_error == 0:
                first_error = layout_result.returncode

    for pane in panes[1:]:
        launch_result = _client.kitten_at(
            "launch", *_launch_argv(pane, is_tab=False, tab_title=None), to=to
        )
        if launch_result.returncode != 0:
            sys.stderr.write(launch_result.stderr)
            return launch_result.returncode if first_error == 0 else first_error
        win_id = int(launch_result.stdout.strip())
        if pane.bg is not None:
            bg_result = _client.kitten_at(
                "set-colors",
                "--match",
                f"id:{win_id}",
                f"background={pane.bg}",
                to=to,
            )
            if bg_result.returncode != 0:
                sys.stderr.write(bg_result.stderr)
                if first_error == 0:
                    first_error = bg_result.returncode

    if tab_accent is not None:
        accent_result = _client.kitten_at(
            "set-tab-color",
            "--match",
            "recent:0",
            f"active_bg={tab_accent}",
            f"inactive_bg={tab_accent}",
            to=to,
        )
        if accent_result.returncode != 0:
            sys.stderr.write(accent_result.stderr)
            if first_error == 0:
                first_error = accent_result.returncode

    return first_error


def cli_scene_launch(args: argparse.Namespace) -> int:
    """CLI handler for ``my-kitty scene launch``."""
    panes: list[Pane] = []
    for s in args.panes:
        try:
            panes.append(parse_pane_spec(s))
        except ValueError as exc:
            sys.stderr.write(f"my-kitty scene launch: {exc}\n")
            return 1
    if not panes:
        sys.stderr.write(
            "my-kitty scene launch: scene launch requires at least one --pane\n"
        )
        return 1
    try:
        return launch_scene(
            args.layout,
            args.tab_title,
            args.tab_accent,
            panes,
            to=args.to,
        )
    except SceneClientError as exc:
        sys.stderr.write(f"my-kitty scene launch: {exc}\n")
        return 1
