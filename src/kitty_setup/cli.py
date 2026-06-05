"""Single binary, subcommand-dispatched CLI for kitty-setup."""

# PYTHON_ARGCOMPLETE_OK
# Owned by the ``my-kitty`` entry point declared in ``pyproject.toml``.
# Subparsers route to handlers defined in their respective modules:
#
# * ``install``   → :func:`kitty_setup.installer.cli_install`
# * ``uninstall`` → :func:`kitty_setup.installer.cli_uninstall`
# * ``doctor``    → :func:`kitty_setup.doctor.cli_doctor`
# * ``prune``     → :func:`kitty_setup.pruner.cli_prune`
# * ``keys``      → :func:`kitty_setup.binding_introspection.cli_keys`
# * ``help``      → top-level help, identical to ``--help``
#
# Per design D4: argparse subparsers, no Click. Per spec: this is the ONLY
# entry point under ``[project.scripts]``. The PYTHON_ARGCOMPLETE_OK magic
# comment above is read by ``register-python-argcomplete`` to enable shell
# tab completion (see add-shell-completion change).

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import argcomplete

from kitty_setup import binding_introspection, doctor, installer, pruner, scenes

PROG: str = "my-kitty"

Handler = Callable[[argparse.Namespace], int]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Install, uninstall, and diagnose the kitty-setup foundation.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_install = sub.add_parser(
        "install",
        help="install kitty + inject config + ensure ~/.local/bin on PATH",
    )
    p_install.add_argument(
        "--no-config",
        action="store_true",
        help="install kitty but skip config injection",
    )
    p_install.add_argument(
        "--dest",
        type=Path,
        default=installer.DEFAULT_DEST,
        help=f"per-user install prefix (default: {installer.DEFAULT_DEST})",
    )
    p_install.set_defaults(func=installer.cli_install)

    p_uninstall = sub.add_parser(
        "uninstall",
        help="remove our entire footprint (default); --keep-* flags preserve subsets",
        description=(
            "Remove our entire footprint by default. Use --keep-* flags to preserve "
            "specific subsets. The my-kitty binary itself is never removed; the "
            "manual `uv tool uninstall my-kitty` command is always printed at the end."
        ),
    )
    p_uninstall.add_argument(
        "--keep-backups",
        dest="keep_backups",
        action="store_true",
        help="preserve every kitty.conf.bak.* file under ~/.config/kitty/",
    )
    p_uninstall.add_argument(
        "--keep-config",
        dest="keep_config",
        action="store_true",
        help="preserve the entire ~/.config/kitty/ footprint (block + payload + backups)",
    )
    p_uninstall.add_argument(
        "--keep-kitty",
        dest="keep_kitty",
        action="store_true",
        help="preserve ~/.local/kitty.app, the kitty symlink, and the desktop entry",
    )
    p_uninstall.set_defaults(func=installer.cli_uninstall)

    p_doctor = sub.add_parser("doctor", help="diagnose install + config-include health")
    p_doctor.set_defaults(func=doctor.cli_doctor)

    p_prune = sub.add_parser(
        "prune",
        help="list / delete accumulated kitty.conf.bak.* backups (opt-in)",
        description=(
            "List or delete accumulated kitty.conf.bak.* files. Without --backups, "
            "only lists (dry run). With --backups, applies one of three policies "
            "(--keep / --older-than / --all). NOTE: pruning --all immediately before "
            "an install reduces rollback safety to the same-process backup."
        ),
    )
    p_prune.add_argument(
        "--backups",
        action="store_true",
        help="actually delete backup files (without this flag the command only lists)",
    )
    policy = p_prune.add_mutually_exclusive_group()
    policy.add_argument(
        "--keep",
        type=int,
        default=None,
        metavar="N",
        help="keep the N most recent backups (default 3 when --backups is passed alone)",
    )
    policy.add_argument(
        "--older-than",
        dest="older_than",
        type=int,
        default=None,
        metavar="DAYS",
        help="delete backups whose mtime is older than DAYS days",
    )
    policy.add_argument(
        "--all",
        action="store_true",
        help="delete every backup file (most aggressive)",
    )
    p_prune.set_defaults(func=pruner.cli_prune)

    p_keys = sub.add_parser(
        "keys",
        help="list active key bindings, grouped by source, with conflicts flagged",
        description=(
            "Enumerate every chord active in the parsed kitty config. Groups "
            "bindings by source file (windowing, clear, etc., plus a "
            "kitty defaults bucket). Annotates intentional overrides and flags "
            "real conflicts."
        ),
    )
    p_keys.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of grouped plain text",
    )
    p_keys.add_argument(
        "--config-path",
        dest="config_path",
        default=None,
        help="path to the kitty config file to load (default: ~/.config/kitty/kitty.conf)",
    )
    p_keys.set_defaults(func=binding_introspection.cli_keys)

    # window / tab — scene primitives (Phase 2 §8, kitty-scenes capability)
    p_window = sub.add_parser(
        "window",
        help="scene primitives that act on a kitty window (title, …)",
    )
    p_window_sub = p_window.add_subparsers(dest="window_action", metavar="<action>")
    p_window_title = p_window_sub.add_parser(
        "title",
        help="set the kitty window title (UTF-8, including emoji)",
    )
    p_window_title.add_argument("text", help="title text")
    p_window_title.add_argument(
        "--temporary",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "if set (default), programs running in the window may override "
            "the title via OSC-2 escape sequences; --no-temporary makes the "
            "title sticky"
        ),
    )
    p_window_title.add_argument(
        "--match",
        type=str,
        default=None,
        metavar="EXPR",
        help="kitty match expression to select the target window",
    )
    p_window_title.add_argument(
        "--to",
        type=str,
        default=None,
        metavar="SOCKET",
        help=(
            "kitty listen-on socket address, e.g. unix:/tmp/kitty; "
            "overrides auto-discovery"
        ),
    )
    p_window_title.set_defaults(func=scenes.title.cli_set_window_title)

    p_window_background = p_window_sub.add_parser(
        "background",
        help="set the per-pane background color (named, #rrggbb, or NONE)",
    )
    p_window_background.add_argument(
        "color",
        help="color: named (blue), hex (#001a33), or NONE to reset",
    )
    p_window_background.add_argument(
        "--match",
        type=str,
        default=None,
        metavar="EXPR",
        help="kitty match expression to select the target pane",
    )
    p_window_background.add_argument(
        "--to",
        type=str,
        default=None,
        metavar="SOCKET",
        help=(
            "kitty listen-on socket address, e.g. unix:/tmp/kitty; "
            "overrides auto-discovery"
        ),
    )
    p_window_background.set_defaults(func=scenes.background.cli_set_window_background)

    p_tab = sub.add_parser(
        "tab",
        help="scene primitives that act on a kitty tab (title, …)",
    )
    p_tab_sub = p_tab.add_subparsers(dest="tab_action", metavar="<action>")
    p_tab_title = p_tab_sub.add_parser(
        "title",
        help="set the kitty tab title (UTF-8, including emoji)",
    )
    p_tab_title.add_argument("text", help="title text")
    p_tab_title.add_argument(
        "--match",
        type=str,
        default=None,
        metavar="EXPR",
        help="kitty match expression to select the target tab",
    )
    p_tab_title.add_argument(
        "--to",
        type=str,
        default=None,
        metavar="SOCKET",
        help=(
            "kitty listen-on socket address, e.g. unix:/tmp/kitty; "
            "overrides auto-discovery"
        ),
    )
    # No --temporary on tab: kitten @ set-tab-title doesn't expose one,
    # and OSC-2 escapes don't route to tab titles regardless.
    p_tab_title.set_defaults(func=scenes.title.cli_set_tab_title)

    p_tab_accent = p_tab_sub.add_parser(
        "accent",
        help="set the kitty tab accent color (active+inactive bg in one call)",
    )
    p_tab_accent.add_argument(
        "color",
        help="color: named (blue), hex (#0066cc), or NONE to reset",
    )
    p_tab_accent.add_argument(
        "--active-fg",
        type=str,
        default=None,
        metavar="COLOR",
        help="foreground color when the tab is focused",
    )
    p_tab_accent.add_argument(
        "--inactive-fg",
        type=str,
        default=None,
        metavar="COLOR",
        help="foreground color when the tab is unfocused",
    )
    p_tab_accent.add_argument(
        "--match",
        type=str,
        default=None,
        metavar="EXPR",
        help="kitty match expression to select the target tab",
    )
    p_tab_accent.add_argument(
        "--to",
        type=str,
        default=None,
        metavar="SOCKET",
        help=(
            "kitty listen-on socket address, e.g. unix:/tmp/kitty; "
            "overrides auto-discovery"
        ),
    )
    p_tab_accent.set_defaults(func=scenes.accent.cli_set_tab_accent)

    # os-window — OS-window-scoped scene primitives (Phase 2 §10).
    # Kitty's architecture binds font size and opacity to the OS window,
    # not the sub-window (pane); the noun makes that explicit.
    p_os_window = sub.add_parser(
        "os-window",
        help="scene primitives that act on the OS window (font-size, opacity)",
    )
    p_os_window_sub = p_os_window.add_subparsers(
        dest="os_window_action", metavar="<action>"
    )

    p_os_window_font = p_os_window_sub.add_parser(
        "font-size",
        help="set the OS-window font size (absolute, relative, or reset)",
    )
    p_os_window_font.add_argument(
        "value",
        type=str,
        help=(
            "font size: absolute (14), relative (+2 / -2 / *1.1 / /2), "
            "or 0 to reset to the configured default"
        ),
    )
    p_os_window_font.add_argument(
        "--all",
        action="store_true",
        help=(
            "apply to all current AND future OS windows (changes the "
            "configured default, per kitten's documented semantics)"
        ),
    )
    p_os_window_font.add_argument(
        "--to",
        type=str,
        default=None,
        metavar="SOCKET",
        help=(
            "kitty listen-on socket address, e.g. unix:/tmp/kitty; "
            "overrides auto-discovery"
        ),
    )
    p_os_window_font.set_defaults(func=scenes.font.cli_set_os_window_font_size)

    p_os_window_opacity = p_os_window_sub.add_parser(
        "opacity",
        help="set the OS-window background opacity (0.0–1.0)",
    )
    p_os_window_opacity.add_argument(
        "value",
        type=float,
        help="opacity 0.0 (transparent) to 1.0 (opaque)",
    )
    p_os_window_opacity.add_argument(
        "--toggle",
        action="store_true",
        help=(
            "reset to default if current opacity equals the requested value, "
            "else set"
        ),
    )
    p_os_window_opacity.add_argument(
        "--all",
        action="store_true",
        help="apply to all current AND future OS windows",
    )
    p_os_window_opacity.add_argument(
        "--to",
        type=str,
        default=None,
        metavar="SOCKET",
        help=(
            "kitty listen-on socket address, e.g. unix:/tmp/kitty; "
            "overrides auto-discovery"
        ),
    )
    p_os_window_opacity.set_defaults(func=scenes.opacity.cli_set_os_window_opacity)

    # scene — composition primitive (Phase 2 §12).
    # Materialises a new tab with a layout + N pre-styled panes in one user
    # gesture, on top of the existing single-noun primitives.
    p_scene = sub.add_parser(
        "scene",
        help="composition primitives (launch a tab with layout + N pre-styled panes)",
    )
    p_scene_sub = p_scene.add_subparsers(dest="scene_action", metavar="<action>")

    p_scene_launch = p_scene_sub.add_parser(
        "launch",
        help=(
            "launch a new tab with a chosen layout and one or more "
            "pre-styled panes in one user gesture"
        ),
        description=(
            "Open a new tab on the running kitty, optionally apply a "
            "layout, spawn one or more --pane groups (each with optional "
            "title / cmd / cwd / bg), and optionally tint the tab accent."
        ),
    )
    p_scene_launch.add_argument(
        "--layout",
        type=str,
        default=None,
        metavar="NAME[:OPTS]",
        help=(
            "kitty layout to apply after the tab is created, e.g. "
            "'tall:mirrored=true'; omit to keep enabled_layouts' default"
        ),
    )
    p_scene_launch.add_argument(
        "--tab-title",
        dest="tab_title",
        type=str,
        default=None,
        metavar="TEXT",
        help="title for the new tab (UTF-8, including emoji)",
    )
    p_scene_launch.add_argument(
        "--tab-accent",
        dest="tab_accent",
        type=str,
        default=None,
        metavar="COLOR",
        help=(
            "accent color for the new tab (named, #rrggbb); applies "
            "only to the focused-tab background"
        ),
    )
    p_scene_launch.add_argument(
        "--pane",
        dest="panes",
        action="append",
        default=[],
        metavar="'key=value,key=value,...'",
        help=(
            "one pane spec; repeatable (at least one required). "
            "Recognised keys: title, cmd, cwd, bg. Commas inside a "
            "value are escaped as '\\,' and backslashes as '\\\\'. "
            "Example: --pane 'title=docker ps,cmd=docker ps,bg=#001f3f'"
        ),
    )
    p_scene_launch.add_argument(
        "--to",
        type=str,
        default=None,
        metavar="SOCKET",
        help=(
            "kitty listen-on socket address, e.g. unix:/tmp/kitty; "
            "overrides auto-discovery"
        ),
    )
    p_scene_launch.set_defaults(func=scenes.launcher.cli_scene_launch)

    def _help_handler(_args: argparse.Namespace) -> int:
        parser.print_help()
        return 0

    p_help = sub.add_parser("help", help="print this help banner")
    p_help.set_defaults(func=_help_handler)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    # No-op when _ARGCOMPLETE is unset in env (interactive runs); short-circuits
    # to candidate emission when the shell is requesting tab completion.
    argcomplete.autocomplete(parser)
    args = parser.parse_args(argv)
    func: Handler | None = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
