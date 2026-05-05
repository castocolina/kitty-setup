## REMOVED Requirements

### Requirement: Single binary on PATH with subcommand dispatch
**Reason**: Capability renamed to `my-kitty-cli` and binary renamed to `my-kitty`. The verbose `my-kitty-setup` form was a stop-gap from the consolidate change; the `-setup` suffix is semantically wrong now that the binary covers install / uninstall / doctor / prune / keys (next).
**Migration**: See the `Single binary on PATH with subcommand dispatch` requirement in the new `my-kitty-cli` capability. Same surface; the binary name on PATH is now `my-kitty`. Users with the legacy `~/.local/bin/my-kitty-setup` shim run `uv tool uninstall my-kitty-setup` — the install prints the exact command.

### Requirement: Install via `uv tool install --force .`, source-independent after install
**Reason**: Capability renamed to `my-kitty-cli`.
**Migration**: See the same-named requirement in the new `my-kitty-cli` capability. Behavior is identical except the binary lands at `~/.local/bin/my-kitty` instead of `~/.local/bin/my-kitty-setup`.

### Requirement: `~/.local/bin` is on PATH after install
**Reason**: Capability renamed to `my-kitty-cli` and the sentinel marker form changed from `# >>> my-kitty-setup PATH >>>` to `# >>> my-kitty PATH >>>`.
**Migration**: See the same-named requirement in the new `my-kitty-cli` capability AND the new `PATH block migration recognizes the legacy marker` requirement, which guarantees that an existing rc file with the legacy marker block is rewritten in place to the new marker form (no duplicate block).

### Requirement: Uninstall has three layered scopes
**Reason**: Capability renamed to `my-kitty-cli`. The printed self-removal command changes from `uv tool uninstall my-kitty-setup` to `uv tool uninstall my-kitty`.
**Migration**: See the same-named requirement in the new `my-kitty-cli` capability. The flag set (`--kitty`, `--self`) and default scope are unchanged.

### Requirement: `make` orchestrates the install and uninstall flows
**Reason**: Capability renamed to `my-kitty-cli`. The `make` targets now invoke `my-kitty install` / `my-kitty uninstall` instead of the longer name.
**Migration**: See the same-named requirement in the new `my-kitty-cli` capability. `make install`, `make uninstall`, `make uninstall ALL=1`, `make prune` semantics unchanged.
