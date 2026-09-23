## ADDED Requirements

### Requirement: Install seeds example scene recipes copy-if-absent

`my-kitty install` SHALL seed the bundled example scene recipes into the user
scenes directory (`$XDG_CONFIG_HOME/kitty-setup/scenes/`, the same directory the
recipe loader reads), creating the directory if it does not exist. The example
recipes SHALL be packaged as data inside the installed wheel (force-included from
`examples/scenes/`, mirroring the existing config-payload packaging) so seeding
works from the installed binary without the source repository present. The
seeding logic SHALL live in the Python install path (`installer.py`), NOT in the
bootstrap shell script — `tools/setup.sh` SHALL NOT copy scene files.

Seeding SHALL be **copy-if-absent per file**: each bundled `*.toml` is copied
only when a file of that name does not already exist in the user scenes
directory. An existing file (including one the user has edited) SHALL NEVER be
overwritten. Seeding SHALL be idempotent and SHALL print a one-line summary of
how many recipes were seeded versus left untouched.

Once copied, a seeded recipe is **user data**: the uninstall path SHALL NOT
remove the user scenes directory or any file in it (consistent with "Uninstall
removes only files written by setup" — the scenes directory lives outside the
managed config payload and is owned by the user thereafter). A user who deletes a
seeded example MAY see it reappear on a subsequent install (an accepted
consequence of copy-if-absent).

#### Scenario: Fresh install seeds the example recipes

- **WHEN** the user runs `my-kitty install` on a host where
  `~/.config/kitty-setup/scenes/` does not yet exist
- **THEN** the directory is created and each bundled example `*.toml` is copied
  into it, and a summary line reports the count seeded

#### Scenario: Re-install never overwrites an edited recipe

- **WHEN** the user has edited `~/.config/kitty-setup/scenes/docker.toml` and then
  runs `my-kitty install` again
- **THEN** the edited `docker.toml` is left byte-for-byte unchanged, any bundled
  example whose name is absent is added, and the summary reports the edited file
  among those kept

#### Scenario: Uninstall leaves seeded scenes in place

- **WHEN** the user runs `my-kitty uninstall` after an install that seeded scenes
- **THEN** the managed config payload and install paths are removed per the
  uninstall contract, but `~/.config/kitty-setup/scenes/` and its `*.toml` files
  remain untouched
