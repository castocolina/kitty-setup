"""Enumerate active kitty key bindings, attribute by source file, flag conflicts.

Backs the ``my-kitty keys`` subcommand and the ``bindings`` check in
``my-kitty doctor``. The implementation is split into:

* :func:`enumerate_bindings` — pure orchestrator. Calls into kitty for the
  parsed keymap (D1), walks our payload files for source attribution (D2),
  reads the allow-list, classifies overrides vs conflicts (D3), returns a
  :class:`Report`.
* :class:`Report` — value object with ``render_text`` / ``to_json`` / counts.
* :func:`cli_keys` — argparse handler bound to the ``keys`` subparser.

See the ``phase1-binding-introspection`` OpenSpec change for spec text and the
four probe artefacts that pin the external-system assumptions.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from kitty_setup import config_updater, installer

DEFAULT_SOURCE: Final[str] = "kitty-default"
ALLOW_LIST_BASENAME: Final[str] = "intentional-overrides.conf"

_MAP_LINE_RE: Final[re.Pattern[str]] = re.compile(r"^\s*map\s+(\S+)\s+(.+?)\s*$")

# probe-phase1-binding-introspection-02: kitty.config.load_config exposes
# Options.keyboard_modes[""].keymap as dict[SingleKey, list[KeyDefinition]].
# The chord is the dict key (SingleKey(mods, key)); KeyDefinition.human_repr()
# returns the ACTION repr, NOT the chord. Convert the SingleKey to a
# canonical "ctrl+shift+t"-style string in the snippet itself, before JSON.
_RUNPY_SNIPPET: Final[str] = (
    "import json, sys\n"
    "from kitty.config import load_config\n"
    "from kitty.fast_data_types import glfw_get_key_name as _glfw_get_key_name\n"
    "opts = load_config(sys.argv[-1])\n"
    'keymap = opts.keyboard_modes[""].keymap\n'
    "out = []\n"
    "for _key, _defs in keymap.items():\n"
    "    _mods = _key.mods\n"
    "    _parts = []\n"
    "    if _mods & 4: _parts.append('ctrl')\n"
    "    if _mods & 1: _parts.append('shift')\n"
    "    if _mods & 2: _parts.append('alt')\n"
    "    if _mods & 8: _parts.append('super')\n"
    "    _name = _glfw_get_key_name(_key.key, False) or 'key_' + str(_key.key)\n"
    "    _parts.append(_name)\n"
    "    _chord = '+'.join(_parts)\n"
    "    for _d in _defs:\n"
    "        out.append({'chord': _chord, 'action': _d.definition})\n"
    "print(json.dumps(out))\n"
)


class BindingIntrospectionError(RuntimeError):
    """Raised when introspection cannot complete (kitty missing, runpy fail, etc.)."""


@dataclasses.dataclass(frozen=True, slots=True)
class Binding:
    chord: str
    action: str
    source: str
    override_of: str | None = None
    conflicts_with: tuple[str, ...] = ()
    redundant: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class Report:
    bindings: tuple[Binding, ...]
    ours_count: int
    defaults_count: int
    conflicts_count: int

    def render_text(self) -> str:
        groups: dict[str, list[Binding]] = {}
        for b in self.bindings:
            groups.setdefault(b.source, []).append(b)

        ordered_sources = sorted(k for k in groups if k != DEFAULT_SOURCE)
        if DEFAULT_SOURCE in groups:
            ordered_sources.append(DEFAULT_SOURCE)

        lines: list[str] = []
        for source in ordered_sources:
            entries = sorted(groups[source], key=lambda b: b.chord)
            label = "kitty defaults" if source == DEFAULT_SOURCE else source
            lines.append(f"{label} ({len(entries)} bindings)")
            for b in entries:
                annotation = ""
                if b.conflicts_with:
                    annotation = f"  [CONFLICT: {'; '.join(b.conflicts_with)}]"
                elif b.redundant:
                    annotation = "  [redundant rebind of kitty default]"
                elif b.override_of is not None:
                    annotation = f"  [overrides default {b.override_of}]"
                lines.append(f"  {b.chord:<22}{b.action}{annotation}")
            lines.append("")

        lines.append(
            f"Summary: {self.ours_count} ours, {self.defaults_count} defaults, "
            f"{self.conflicts_count} conflict{'s' if self.conflicts_count != 1 else ''}."
        )
        return "\n".join(lines)

    def to_json(self) -> str:
        payload = {
            "bindings": [
                {
                    "chord": b.chord,
                    "action": b.action,
                    "source": b.source,
                    "override_of": b.override_of,
                    "conflicts_with": list(b.conflicts_with),
                    "redundant": b.redundant,
                }
                for b in self.bindings
            ],
            "summary": {
                "ours": self.ours_count,
                "defaults": self.defaults_count,
                "conflicts": self.conflicts_count,
            },
        }
        return json.dumps(payload, indent=2, sort_keys=False)


def _resolve_kitty_bin() -> Path:
    on_path = shutil.which("kitty")
    if on_path is not None:
        return Path(on_path)
    candidates = [installer.SYMLINK_PATH, installer._kitty_bin(installer.DEFAULT_DEST)]
    for c in candidates:
        if c.is_file() or c.is_symlink():
            return c
    raise BindingIntrospectionError(
        "kitty binary not found on PATH, in ~/.local/bin, or under ~/.local/kitty.app"
    )


def _run_kitty_runpy(kitty_bin: Path, conf_path: Path) -> list[dict[str, str]]:
    """Invoke ``kitty +runpy <snippet> <conf_path>``; return parsed JSON list."""
    try:
        result = subprocess.run(  # noqa: S603 — args are constructed from trusted paths
            [str(kitty_bin), "+runpy", _RUNPY_SNIPPET, str(conf_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
    except FileNotFoundError as exc:
        raise BindingIntrospectionError(f"kitty binary not executable: {kitty_bin}") from exc
    if result.returncode != 0:
        raise BindingIntrospectionError(
            f"kitty +runpy exited {result.returncode}: {result.stderr.strip() or '<no stderr>'}"
        )
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise BindingIntrospectionError(
            f"could not parse kitty +runpy output: {result.stdout!r}"
        ) from exc


# probe-phase1-binding-introspection-03: definition_location is empty after parse.
# Source attribution comes from a manual pre-walk of our payload files instead.
def _walk_payload(payload_dir: Path) -> dict[tuple[str, str], str]:
    """Map ``(chord, action) -> source basename`` for every ``map`` line we wrote."""
    if not payload_dir.is_dir():
        return {}
    out: dict[tuple[str, str], str] = {}
    for conf in sorted(payload_dir.glob("*.conf")):
        if conf.name == ALLOW_LIST_BASENAME or conf.name == "kitty-setup.conf":
            continue
        basename = conf.stem
        for raw_line in conf.read_text(encoding="utf-8").splitlines():
            match = _MAP_LINE_RE.match(raw_line)
            if match is None:
                continue
            chord, action = match.group(1).strip(), match.group(2).strip()
            out[(chord, action)] = basename
    return out


def _read_allow_list(path: Path) -> set[str]:
    """Return the set of chord strings authorised as intentional overrides."""
    if not path.is_file():
        return set()
    chords: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip inline comments after the chord token (e.g. "ctrl+shift+t  # foo").
        chord = line.split("#", 1)[0].strip()
        if chord:
            chords.add(chord)
    return chords


# probe-phase1-binding-introspection-04: duplicate `map` directives appear as
# multiple KeyDefinition entries in defs[]; conflict detection is len(defs) > 1
# minus the allow-listed-default case (D3).
def _classify(
    raw_bindings: Iterable[dict[str, str]],
    payload_map: dict[tuple[str, str], str],
    allow_list: set[str],
) -> tuple[list[Binding], int, int, int]:
    """Group raw bindings by chord and classify; return (bindings, ours, defaults, conflicts)."""
    by_chord: dict[str, list[dict[str, str]]] = {}
    for entry in raw_bindings:
        by_chord.setdefault(entry["chord"], []).append(entry)

    bindings: list[Binding] = []
    ours_count = 0
    defaults_count = 0
    conflicts_count = 0

    for chord, entries in by_chord.items():
        # Attribute each (chord, action) to our payload at most once. Kitty's
        # parsed keymap reports both the upstream default AND our redundant
        # rebind as separate entries with identical action, so a naive lookup
        # double-attributes them to our source. Keep the first hit ours; the
        # rest are kitty defaults of the same shape (D5 redundant rebinds).
        sources: list[str] = []
        consumed: set[tuple[str, str]] = set()
        for e in entries:
            key = (chord, e["action"])
            if key in payload_map and key not in consumed:
                sources.append(payload_map[key])
                consumed.add(key)
            else:
                sources.append(DEFAULT_SOURCE)
        is_multi = len(entries) > 1
        # Intentional override: exactly 2 defs, exactly one from us, exactly one default,
        # AND chord is allow-listed.
        ours_in_chord = [s for s in sources if s != DEFAULT_SOURCE]
        defaults_in_chord = [s for s in sources if s == DEFAULT_SOURCE]
        # Redundant rebind: every def on this chord carries the same action.
        # That means our `map` line restates kitty's default verbatim — the
        # parsed keymap surfaces both entries, but they are semantically
        # equivalent. Suppress the false "two of ours = conflict" by treating
        # the our-side entry as a redundant rebind (no override, no conflict).
        # No allow-list entry is required for this case; the same-(chord, action)
        # equality is itself the proof. See phase1-curated-bindings-revert-defaults
        # design D7.
        unique_actions = {e["action"] for e in entries}
        is_redundant_rebind = (
            is_multi
            and len(unique_actions) == 1
            and len(ours_in_chord) >= 1
            and len(defaults_in_chord) >= 1
        )
        is_intentional_override = (
            is_multi
            and not is_redundant_rebind
            and len(entries) == 2
            and len(ours_in_chord) == 1
            and len(defaults_in_chord) == 1
            and chord in allow_list
        )
        # A chord is OUR conflict only when at least one def is ours. Pure
        # kitty-default multi-defs (e.g. kitty cycles ctrl+shift+a through four
        # opacity actions by design) are kitty's own surface, not our bug.
        # Redundant rebinds are not conflicts (handled above).
        is_conflict = (
            is_multi
            and not is_intentional_override
            and not is_redundant_rebind
            and len(ours_in_chord) >= 1
        )

        for entry, source in zip(entries, sources, strict=True):
            override_of: str | None = None
            conflicts_with: tuple[str, ...] = ()
            redundant = False
            if is_redundant_rebind and source != DEFAULT_SOURCE:
                redundant = True
            elif is_intentional_override and source != DEFAULT_SOURCE:
                # Annotate the OUR-side binding with the default it overrides.
                default_action = next(
                    e["action"]
                    for e, s in zip(entries, sources, strict=True)
                    if s == DEFAULT_SOURCE
                )
                override_of = default_action
            elif is_conflict and source != DEFAULT_SOURCE:
                # Annotate only the OUR-side binding(s) with the collision detail.
                # The kitty-default entry stays in the report (it counts toward
                # the `defaults` total) but renders without a conflict annotation
                # so the "kitty defaults" section stays clean.
                conflicts_with = tuple(
                    (
                        f"kitty default {e['action']}"
                        if s == DEFAULT_SOURCE
                        else f"also in {s}: {e['action']}"
                    )
                    for e, s in zip(entries, sources, strict=True)
                    if e is not entry
                )
            bindings.append(
                Binding(
                    chord=chord,
                    action=entry["action"],
                    source=source,
                    override_of=override_of,
                    conflicts_with=conflicts_with,
                    redundant=redundant,
                )
            )
            if source == DEFAULT_SOURCE:
                defaults_count += 1
            else:
                ours_count += 1

        if is_conflict:
            conflicts_count += 1

    return bindings, ours_count, defaults_count, conflicts_count


def enumerate_bindings(
    conf_path: Path,
    *,
    kitty_bin: Path | None = None,
    payload_dir: Path | None = None,
    allow_list_path: Path | None = None,
) -> Report:
    """Build a :class:`Report` for ``conf_path``."""
    resolved_kitty = kitty_bin or _resolve_kitty_bin()
    resolved_payload = payload_dir or config_updater.ConfigPaths.for_user().payload_dir
    resolved_allow = allow_list_path or (resolved_payload / ALLOW_LIST_BASENAME)

    raw = _run_kitty_runpy(resolved_kitty, conf_path)
    payload_map = _walk_payload(resolved_payload)
    allow_list = _read_allow_list(resolved_allow)
    bindings, ours, defaults, conflicts = _classify(raw, payload_map, allow_list)
    return Report(
        bindings=tuple(bindings),
        ours_count=ours,
        defaults_count=defaults,
        conflicts_count=conflicts,
    )


def cli_keys(args: argparse.Namespace) -> int:
    """Handler for ``my-kitty keys``."""
    conf_path = (
        Path(args.config_path).expanduser()
        if args.config_path is not None
        else config_updater.ConfigPaths.for_user().conf_file
    )
    try:
        report = enumerate_bindings(conf_path)
    except BindingIntrospectionError as exc:
        print(f"keys: introspection failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(report.to_json())
    else:
        print(report.render_text())
    return 0
