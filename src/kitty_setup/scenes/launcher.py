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
import json
import os
import subprocess
import sys
from dataclasses import dataclass, replace

from kitty_setup.scenes import _client
from kitty_setup.scenes._client import SceneClientError
from kitty_setup.scenes.colors import ColorError, normalize_color

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
            raise ValueError(f"malformed pane spec; expected key=value, got '{seg}'")
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
    default_cwd: str | None,
) -> list[str]:
    """Build the argv tail for one ``kitten @ launch`` call (kitten verb omitted).

    ``default_cwd`` is the directory the scene was launched from; it is applied
    to any pane that does not set its own ``cwd``, so a scene opens in the
    directory you invoked it from rather than kitty's startup dir.
    """
    args: list[str] = ["--type=tab" if is_tab else "--type=window", "--hold"]
    if is_tab and tab_title is not None:
        args.append(f"--tab-title={tab_title}")
    if pane.title is not None:
        args.append(f"--title={pane.title}")
    cwd = pane.cwd if pane.cwd is not None else default_cwd
    if cwd is not None:
        args.append(f"--cwd={cwd}")
    if pane.cmd is not None:
        args.extend(["bash", "-lc", pane.cmd])
    return args


def _apply_bg(win_id: int, bg: str | None, to: str | None, first_error: int) -> int:
    """Fail-soft ``set-colors`` for one pane; return the updated first_error."""
    if bg is None:
        return first_error
    result = _client.kitten_at("set-colors", "--match", f"id:{win_id}", f"background={bg}", to=to)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        if first_error == 0:
            return result.returncode
    return first_error


def _fail_soft(result: subprocess.CompletedProcess[str], first_error: int) -> int:
    """Print stderr on non-zero, record the first non-zero exit, never raise."""
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        if first_error == 0:
            return result.returncode
    return first_error


def _origin_window() -> int | None:
    """The id of the kitty window the scene is launched from, or ``None``.

    kitty exports ``$KITTY_WINDOW_ID`` into every window's environment, so a
    ``my-kitty`` invoked from a shell inside kitty inherits it. ``None`` when
    ``my-kitty`` runs outside kitty (no window to reuse) — e.g. driven over a
    socket from another terminal, or from the integration harness.
    """
    raw = os.environ.get("KITTY_WINDOW_ID")
    return int(raw) if raw and raw.isdigit() else None


def _origin_tab_is_solo(origin_window: int, to: str | None) -> bool:
    """True only when the origin window's tab holds exactly one window.

    Queries ``kitten @ ls`` and counts the windows of the tab that contains
    ``origin_window``. Returns ``False`` on ANY uncertainty — a non-zero ``ls``,
    unparseable JSON, or an origin id absent from the tree. Fail-safe by design:
    we only fill the current tab when we can *prove* it holds exactly the origin
    window, so an ambiguous state opens a fresh tab rather than risk piling new
    windows onto a populated one (the probe-observable lesson: verify the tab's
    window count, don't infer it from "inside kitty").
    """
    result = _client.kitten_at("ls", to=to)
    if result.returncode != 0:
        return False
    try:
        tree = json.loads(result.stdout)
    except (ValueError, TypeError):
        return False
    for osw in tree:
        for tab in osw.get("tabs", []):
            windows = tab.get("windows", [])
            if any(w.get("id") == origin_window for w in windows):
                return len(windows) == 1
    return False


def _fill_current_tab(
    layout: str | None,
    tab_title: str | None,
    tab_accent: str | None,
    panes: list[Pane],
    *,
    to: str | None,
    default_cwd: str | None,
    origin_window: int,
) -> int:
    """Materialise a multi-pane scene INTO the current tab (no new tab).

    Used when ``my-kitty`` runs inside kitty (``$KITTY_WINDOW_ID`` is set): the
    window the scene was launched from becomes pane 0 (restyled in place), the
    remaining panes open as ``--type=window`` splits in the same tab, and
    ``layout`` / ``tab_title`` / ``tab_accent`` are applied to that current tab
    (kitty defaults ``goto-layout`` / ``set-tab-title`` / ``set-tab-color`` to
    the focused tab — probe-verified, so no ``--match`` is needed). The reused
    window already sits in the launch directory, so ``default_cwd`` is applied
    only to the freshly launched panes; an explicit pane-0 ``cwd``/``cmd`` is
    best-effort fed to the reused shell via ``send-text``.
    """
    first_error = 0
    p0 = panes[0]

    # Pane 0 = the window we were launched from: restyle it in place.
    if p0.title is not None:
        first_error = _fail_soft(
            _client.kitten_at(
                "set-window-title", "--match", f"id:{origin_window}", p0.title, to=to
            ),
            first_error,
        )
    first_error = _apply_bg(origin_window, p0.bg, to, first_error)
    if p0.cwd is not None:
        first_error = _fail_soft(
            _client.kitten_at(
                "send-text", "--match", f"id:{origin_window}", f"cd {p0.cwd}\n", to=to
            ),
            first_error,
        )
    if p0.cmd is not None:
        first_error = _fail_soft(
            _client.kitten_at("send-text", "--match", f"id:{origin_window}", f"{p0.cmd}\n", to=to),
            first_error,
        )

    # Remaining panes: new windows in the SAME (current) tab.
    for pane in panes[1:]:
        launch_result = _client.kitten_at(
            "launch",
            *_launch_argv(pane, is_tab=False, tab_title=None, default_cwd=default_cwd),
            to=to,
        )
        if launch_result.returncode != 0:
            sys.stderr.write(launch_result.stderr)
            return launch_result.returncode if first_error == 0 else first_error
        win_id = int(launch_result.stdout.strip())
        first_error = _apply_bg(win_id, pane.bg, to, first_error)

    # Layout + tab styling target the focused tab (no --match needed).
    if layout is not None:
        first_error = _fail_soft(_client.kitten_at("goto-layout", layout, to=to), first_error)
    if tab_title is not None:
        first_error = _fail_soft(_client.kitten_at("set-tab-title", tab_title, to=to), first_error)
    if tab_accent is not None:
        first_error = _fail_soft(
            _client.kitten_at(
                "set-tab-color", f"active_bg={tab_accent}", f"inactive_bg={tab_accent}", to=to
            ),
            first_error,
        )
    return first_error


def launch_scene(
    layout: str | None,
    tab_title: str | None,
    tab_accent: str | None,
    panes: list[Pane],
    *,
    to: str | None = None,
    default_cwd: str | None = None,
    origin_window: int | None = None,
) -> int:
    """Materialise a scene on the running kitty; return the first non-zero exit.

    When ``origin_window`` is set (the id of the window the scene is launched
    from — ``$KITTY_WINDOW_ID``), the scene has **two or more panes**, AND the
    origin window's tab holds **exactly one window** (`_origin_tab_is_solo`), the
    scene is built INTO the current tab: the origin window becomes pane 0 and the
    rest open as splits beside it (see :func:`_fill_current_tab`). No new tab is
    created. If the current tab already holds other windows (or the count cannot
    be determined), the scene falls through to the new-tab path below — so it
    never piles panes onto a populated tab. This is the in-kitty path, so a
    multi-pane scene launched from a shell in a solo tab never steals a separate
    tab.

    Otherwise (``origin_window`` is ``None`` — e.g. driven over a socket from
    another terminal):

    A scene with **exactly one pane** launches that pane as a ``--type=window``
    into the CURRENT tab — no new tab is created, and ``layout`` / ``tab_title``
    / ``tab_accent`` are not applied (there is no new tab to own them). A scene
    with two or more panes opens a new tab, following the probe-grounded kitten
    call algorithm (``design.md`` D3):

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

    ``default_cwd`` (typically the caller's ``os.getcwd()``) is applied as the
    cwd of every pane that does not set its own ``cwd`` — the tab AND its
    windows open in the directory the scene was launched from.

    Fail-hard on ``launch`` non-zero (propagate exit code, stop processing).
    Fail-soft on ``set-colors`` and ``set-tab-color`` (print stderr, record
    the exit code, continue). Returns the first non-zero exit code, or ``0``
    if all calls succeed.

    Raises :class:`SceneClientError` (from :mod:`._client`) on socket discovery
    failures; callers should catch and surface via ``cli_scene_launch``.
    """
    if not panes:
        raise ValueError("launch_scene requires at least one Pane")

    # Normalize every color BEFORE the first kitten call — an unrecognized color
    # raises ColorError here, so a scene is rejected without opening any window.
    tab_accent = normalize_color(tab_accent)
    panes = [replace(p, bg=normalize_color(p.bg)) for p in panes]

    first_error: int = 0
    single = len(panes) == 1

    # In-kitty multi-pane: fill the CURRENT tab ONLY when it holds exactly the
    # origin window (a "solo" tab). If the tab already has other windows — or we
    # cannot prove it is solo — fall through to the new-tab path so we never pile
    # the scene's panes onto a populated tab.
    if origin_window is not None and not single and _origin_tab_is_solo(origin_window, to):
        return _fill_current_tab(
            layout,
            tab_title,
            tab_accent,
            panes,
            to=to,
            default_cwd=default_cwd,
            origin_window=origin_window,
        )

    # First pane: a single-pane scene launches a WINDOW into the current tab; a
    # multi-pane scene opens a new tab carrying the tab title.
    p0 = panes[0]
    result = _client.kitten_at(
        "launch",
        *_launch_argv(
            p0,
            is_tab=not single,
            tab_title=None if single else tab_title,
            default_cwd=default_cwd,
        ),
        to=to,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    win0 = int(result.stdout.strip())
    first_error = _apply_bg(win0, p0.bg, to, first_error)

    if single:
        # The lone window joined the current tab; no tab layout/title/accent.
        return first_error

    if layout is not None:
        layout_result = _client.kitten_at("goto-layout", layout, to=to)
        if layout_result.returncode != 0:
            sys.stderr.write(layout_result.stderr)
            if first_error == 0:
                first_error = layout_result.returncode

    for pane in panes[1:]:
        launch_result = _client.kitten_at(
            "launch",
            *_launch_argv(pane, is_tab=False, tab_title=None, default_cwd=default_cwd),
            to=to,
        )
        if launch_result.returncode != 0:
            sys.stderr.write(launch_result.stderr)
            return launch_result.returncode if first_error == 0 else first_error
        win_id = int(launch_result.stdout.strip())
        first_error = _apply_bg(win_id, pane.bg, to, first_error)

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
    """CLI handler for ``my-kitty scene launch``.

    Two mutually exclusive modes (design D1):

    * ``scene launch <name>`` — load the named TOML recipe and materialise it
      (the recipe file is authoritative; inline style flags are rejected).
    * ``scene launch --pane …`` — the imperative inline form (unchanged).
    """
    name: str | None = getattr(args, "name", None)
    if name is not None:
        return _launch_named_scene(name, args)
    return _launch_inline_scene(args)


def _launch_named_scene(name: str, args: argparse.Namespace) -> int:
    """Name mode: forbid inline flags, load the recipe, then launch it."""
    # Local import avoids a load-time cycle (recipe imports Pane from this module).
    from kitty_setup.scenes import recipe

    if args.panes:
        sys.stderr.write(
            "my-kitty scene launch: a scene name and inline --pane flags are "
            "contradictory; use one or the other\n"
        )
        return 1
    if args.layout is not None or args.tab_title is not None or args.tab_accent is not None:
        sys.stderr.write(
            "my-kitty scene launch: --layout/--tab-title/--tab-accent are not "
            "accepted with a named scene; the recipe file is authoritative\n"
        )
        return 1
    try:
        layout, tab_title, tab_accent, panes = recipe.load_scene(name)
    except recipe.SceneRecipeError as exc:
        sys.stderr.write(f"my-kitty scene launch: {exc}\n")
        return 1
    try:
        return launch_scene(
            layout,
            tab_title,
            tab_accent,
            panes,
            to=args.to,
            default_cwd=os.getcwd(),
            origin_window=_origin_window(),
        )
    except ColorError as exc:
        sys.stderr.write(f"my-kitty scene launch: {exc}\n")
        return 1
    except SceneClientError as exc:
        sys.stderr.write(f"my-kitty scene launch: {exc}\n")
        return 1


def _launch_inline_scene(args: argparse.Namespace) -> int:
    """Inline mode: parse each ``--pane`` group and launch (unchanged behavior)."""
    panes: list[Pane] = []
    for s in args.panes:
        try:
            panes.append(parse_pane_spec(s))
        except ValueError as exc:
            sys.stderr.write(f"my-kitty scene launch: {exc}\n")
            return 1
    if not panes:
        sys.stderr.write(
            "my-kitty scene launch: scene launch requires a scene name or at " "least one --pane\n"
        )
        return 1
    try:
        return launch_scene(
            args.layout,
            args.tab_title,
            args.tab_accent,
            panes,
            to=args.to,
            default_cwd=os.getcwd(),
            origin_window=_origin_window(),
        )
    except ColorError as exc:
        sys.stderr.write(f"my-kitty scene launch: {exc}\n")
        return 1
    except SceneClientError as exc:
        sys.stderr.write(f"my-kitty scene launch: {exc}\n")
        return 1
