# Verification — phase2-scene-launcher

Verified 2026-06-05 on the user's daily host (Pop!_OS 24.04 + COSMIC + kitty 0.47.1).

## `make doctor`

```
PASS kitty binary: /home/user-zero/.local/bin/kitty -> kitty 0.47.1 created by Kovid Goyal
PASS symlink: /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
PASS desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
PASS config payload: /home/user-zero/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/user-zero/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 22 ours, 79 defaults, 0 conflicts
PASS completion: helper /usr/bin/register-python-argcomplete; eval line present in /home/user-zero/.zshrc
PASS remote-control: reachable on 1 kitty instance
```

## Tests

`uv run pytest tests/unit/` → **195 passed**.

`KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h25_scene_launcher.py -v`:

```
tests/integration/test_h25_scene_launcher.py::test_launch_tab_combines_tab_title_window_title_cwd_and_cmd_in_one_call PASSED
tests/integration/test_h25_scene_launcher.py::test_startup_command_accepts_bare_argv_bash_lc_and_compound_shell PASSED
tests/integration/test_h25_scene_launcher.py::test_launch_stdout_is_window_id_and_recent_zero_still_targets_after_no_response PASSED
tests/integration/test_h25_scene_launcher.py::test_new_tab_focuses_synchronously_subsequent_window_launches_land_in_new_tab PASSED
tests/integration/test_h25_scene_launcher.py::test_three_pane_scene_takes_six_kitten_calls_with_mirrored_tall_and_distinct_titles PASSED
tests/integration/test_my_kitty_scene_launch_cli_creates_three_pane_tab PASSED
6 passed
```

`KITTI_INTEGRATION=1 uv run pytest tests/` → **255 passed** (after the unrelated
`test_h19_bindings_revert` fixture was updated for kitty 0.47.x smooth-scroll
defaults in a separate commit).

## `openspec validate phase2-scene-launcher --strict`

```
Change 'phase2-scene-launcher' is valid
```

## `my-kitty scene launch --help` (excerpt)

```
usage: my-kitty scene launch [-h] [--layout NAME[:OPTS]] [--tab-title TEXT]
                             [--tab-accent COLOR]
                             [--pane 'key=value,key=value,...'] [--to SOCKET]

  --layout NAME[:OPTS]  kitty layout to apply after the tab is created
  --tab-title TEXT      title for the new tab (UTF-8, including emoji)
  --tab-accent COLOR    accent color for the new tab (named, #rrggbb)
  --pane 'key=value,...'  one pane spec; repeatable (at least one required).
                          Recognised keys: title, cmd, cwd, bg.
```

## Completion + keys

- argcomplete suggests `scene` as a top-level candidate (verified via fd8).
- `my-kitty keys` → `Summary: 22 ours, 79 defaults, 0 conflicts` — unchanged.

## Manual verification (§8.3)

User ran the docker-monitor recipe:

```
my-kitty scene launch --layout=tall:mirrored=true --tab-title="🐳 docker-mon" \
  --tab-accent=#ff851b --pane 'title=ps,cmd=docker ps' \
  --pane 'title=stats,bg=#001f3f,cmd=docker stats' --pane 'title=shell'
```

Confirmed: new tab with mirrored Tall layout, three named panes (ps/stats/shell),
p2 tinted dark blue, orange tab accent. User: "funciona 100%".

## Bug found + fixed during apply

The tab-accent call originally emitted `set-tab-color ... active=<color>`, which
kitty rejects with `active is not a valid color name`. Fixed to
`active_bg=<color> inactive_bg=<color>` (mirrors the `accent.py` primitive). The
h25 e2e test now passes `--tab-accent` and asserts the CLI exit code is 0, so the
real `set-tab-color` call is exercised — not just argv composition. (Per the
"probe observables, not just exit-code" lesson.)
