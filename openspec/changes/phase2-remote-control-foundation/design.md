## Context

Phase 2 of `docs/requirements.md` is a stack of "scenes" capabilities (§8-§14) that all need to drive the user's running kitty over its remote-control socket. Today's managed payload exposes zero RC surface to the user's daily kitty. The integration harness has its own per-session RC (via CLI flags), but that helps tests, not Phase 2 scripts the user invokes from a shell or a chord.

Current state:
- `config/kitty/kitty-setup.conf` includes nine per-topic files; none of them sets `allow_remote_control` or `listen_on`.
- `config/kitty/broadcast.conf` uses `--allow-remote-control` on a single `launch` line — that flag toggles RC for the spawned broadcast kitten window, not the whole instance.
- `src/kitty_setup/harness/` spawns kitty with `-o allow_remote_control=yes --listen-on=unix:tmp/sessions/<id>/sock` per-session. This proves the mechanism but is invisible to the user's daily kitty.
- `src/kitty_setup/doctor.py` reports six checks (kitty path/version, include block presence, parse exit, payload paths, desktop entry, bindings). It has no RC reachability check.

Stakeholder is the user (single-user repo). Constraint is the project rule "scripts before integration, hypothesis before implementation, no helper layer until at least one Phase 2 caller exists." So this change ships the minimum surface — one `.conf` file, one include line, one doctor check, one probe, one repro — and nothing else.

## Goals / Non-Goals

**Goals:**

- Expose a stable, per-instance unix socket from the user's daily kitty, reachable by any process running as the same UID.
- Pick a socket path identical on Linux and macOS so Phase 2 scripts can target it without OS-specific branches in their `kitty @ --to <socket>` argument.
- Surface the reachability of that socket in `my-kitty doctor` as a best-effort check that does not fail when no kitty is running.
- Land the surface with zero perceived behaviour change for the user. No new chords. No new commands. Phase 1 keeps working byte-identical above the new include line.
- Preserve the surgical install/uninstall contract from `kitty-config-management`.

**Non-Goals:**

- No Phase 2 capability code. §8-§14 each land in their own change on top of this one.
- No helper binary or Python wrapper around `kitty @`. Premature — wait for a real Phase 2 caller before abstracting.
- No password-protected RC. Single-user host, local-only socket, standard POSIX perms. The trade-off is recorded in D2 below.
- No harness rework. The harness keeps its per-session `--listen-on` flow; it does not read the new `remote-control.conf`.
- No image-paste (§7) work. Paused until reproducible repro lands.
- No tmux-side guidance. Out of tree for this change (same precedent as the §4 pause note).

## Decisions

### D1. Socket-path strategy: `unix:/tmp/kitty`, kitty auto-appends `-<PID>` (Linux verified; macOS deferred)

Use one literal `listen_on` value on both platforms:

```
listen_on unix:/tmp/kitty
```

Kitty's documented `listen_on` semantics append the kitty PID to the path automatically — the resolved socket lands at `/tmp/kitty-<PID>`. The earlier draft of this design used `unix:/tmp/kitty-$KITTY_PID` under the assumption that `$KITTY_PID` is a recognised expansion variable in `listen_on` values. **Probe 01 falsified that assumption** — the literal string `$KITTY_PID` is NOT substituted; the broken-looking socket `/tmp/kitty-$KITTY_PID-<PID>` is created instead. The fix is to drop the placeholder; kitty's own auto-suffix produces the per-instance path we wanted. The path is filesystem-scoped, per-instance (no cross-instance leakage — verified by probe 02), and resolvable by any tool that knows the kitty PID. macOS treats `/tmp` as a symlink to `/private/tmp`; unix sockets work transparently through that symlink (assumption, deferred to probe 05).

**Alternatives considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| `unix:@kitty-$KITTY_PID` (abstract socket, Linux-only) | No FS entry to clean up | Linux-only; breaks D1's "one literal value both platforms" goal | Rejected — cross-platform parity wins |
| `unix:$XDG_RUNTIME_DIR/kitty-$KITTY_PID` | RFC-aligned runtime dir on Linux | `$XDG_RUNTIME_DIR` is unset by default on macOS; would force a platform branch | Rejected — branch defeats the goal |
| `unix:/tmp/kitty` (no `$KITTY_PID`) | Simpler | Two concurrent kitty instances clash on the same path; second one fails to listen | Rejected — breaks multi-instance |
| `tcp:localhost:<port>` | Cross-host friendly | Wider attack surface, port pick problem, no local-uid scoping | Rejected — exceeds requirement |

**Probe gate (h21):** the corrected literal value `listen_on unix:/tmp/kitty` was verified end-to-end by probes 01-04 on Linux (Wayland, kitty 0.46.2) before promotion. The macOS leg is deferred-with-reason per probe 05; the repro doc carries the same `## macOS Status: deferred-with-reason` pattern as §5/§6.

### D2. RC mode: `allow_remote_control yes`, not `socket-only` or `password`

`allow_remote_control yes` enables RC over any of {kitty's CLI `--listen-on`, OSC 52 clipboard, the listen socket, the launch-from-chord path}. The single-user, local-only context means the simpler mode is the right default.

**Alternatives considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| `socket-only` | Restricts RC to the unix socket; rejects the same-window `kitty @` shortcut | Phase 2 chords that invoke RC from inside kitty would break unless explicitly routed via the socket; ergonomic regression for no real security gain on a single-user host | Rejected for v1; can tighten later if multi-user case arrives |
| `password` | Defence against same-user processes calling RC | False security: any process running as the user can read the password file; against malicious peers, only true sandboxing helps; the local-UID model already covers the realistic threat | Rejected |
| `no` | Status quo | Phase 2 dead on arrival | N/A — that's the bug |

**Security trade-off recorded:** any process running as the user's UID can call `kitty @` against the socket. The socket is owned by the user, with a file mode equal to `0777 & ~umask` of the spawning shell (probe 03 observed `0775` under `umask 0022`; kitty does NOT chmod the socket to `0600`). Access scoping is enforced by the kernel's UDS permission check against the calling process's UID, not by file mode bits alone. On a multi-user host this would warrant `password` or `socket-only`, plus an explicit `chmod 0600` post-spawn; on a single-user dev box it does not. Flag for revisit if the project ever ships for multi-user hosts.

### D3. Doctor check: best-effort, never fails on "no kitty running"

A reachability check at `make doctor` time has two modes:

- **No kitty running on this host:** `SKIP remote-control: no running kitty` and exit-code-friendly. Reason: doctor must stay green right after `make setup` on a host where the user has not yet launched kitty for the first time.
- **Kitty running:** resolve the socket path from `remote-control.conf` (parsed, not hardcoded), substitute `$KITTY_PID` from each running kitty PID (`pgrep -x kitty` or platform equivalent), and call `kitty @ --to unix:<path> ls` against each. Report `PASS remote-control: reachable on <N> kitty instance(s)` or `FAIL remote-control: <path> not reachable: <stderr>`.

The check is read-only and uses no `sudo`. Implementation lives in `src/kitty_setup/doctor.py` alongside the other six checks; no new module, no new subcommand.

**Alternatives considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Always FAIL when no kitty is running | Catches "user never opened kitty after install" | False positive immediately after install — the install is correct, the user just hasn't launched | Rejected |
| Skip the check entirely | Less code | No diagnostic for "Phase 2 script can't reach kitty"; doctor is exactly where that diagnostic belongs | Rejected |
| Run the check only when invoked as `my-kitty doctor --check remote-control` | Opt-in, no false positives | Adds a CLI flag for one check; introduces shape that other checks don't follow | Rejected — keep doctor simple |

### D4. Hypothesis shape (h21): probe drives an out-of-session RC call

The autonomous probe at `tmp/h21-remote-control-foundation/run.py` MUST verify the "user-facing daily kitty" scenario, not just the harness scenario:

1. Spawn a `KittySession` with a session-local config that includes a verbatim copy of `remote-control.conf`. The session's own `--listen-on` flag still points at its session socket (this is the harness's invariant); the *included config's* `listen_on` is what the test exercises.
2. Inside the session, run `kitty @ --to env KITTY_LISTEN_ON ls` from a shell window (or read the env var directly via `KittySession.send_text` + `get_text`). Capture the resolved path.
3. From the test process — *outside* the session's harness socket — call `kitty @ --to unix:/tmp/kitty-<resolved-pid> ls` and assert the call returns JSON listing the session's tabs/windows.

Step 3 is the load-bearing assertion: it proves the config-level `listen_on` works for a process that does not have the harness's CLI-flag knowledge. That is the Phase 2 scenario.

**Open assumption to verify in probe-01:** that kitty's `$KITTY_PID` placeholder in `listen_on` resolves to the kitty process PID at startup, not at config-parse time, and that the resolved socket survives kitty restarts (different PID, different socket, predictable expansion). Documented kitty behaviour says yes; probe verifies.

### D5. Doctor check shape vs `kitty-install` requirement on doctor

The existing `kitty-install` spec lists six checks for doctor. Adding a seventh is a requirement-level change in principle, but the existing spec uses an enumeration of six items with "AND" connectors. Two paths:

- **Path A — modify `kitty-install` spec.** Update the doctor requirement to add the new check and its `SKIP/PASS/FAIL` semantics.
- **Path B — leave `kitty-install` alone; add the check semantics under a new requirement in `kitty-remote-control`.**

Picking **Path A**. The doctor command is owned by `kitty-install` per the existing spec; adding a check is a MODIFIED requirement on that capability, not a new capability. The new `kitty-remote-control` spec describes the *behaviour of the socket and the .conf file*; it should not also describe how the diagnostic surface is wired. Captured in tasks.md as a `MODIFIED Requirements` delta under `specs/kitty-install/spec.md`.

### D6. Where the new include line goes in `kitty-setup.conf`

Append at the end of the include list, after `monitor.conf`. Two reasons:

- The order of kitty config includes matters only for `map`/`mouse_map` (last write wins). `allow_remote_control` and `listen_on` are global directives; placement has no semantic effect.
- Trailing-position placement makes the diff for this change a one-line append, easier to review and easier to revert.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| `$KITTY_PID` does not expand in `listen_on` value | Confirmed false by probe 01 — `$KITTY_PID` is not an expansion variable. Mitigation adopted: write `listen_on unix:/tmp/kitty` and rely on kitty's documented auto-suffix `-<PID>`. Open Question OQ-1 resolved. |
| Two concurrent kitty instances written by the same user collide on socket creation | `$KITTY_PID` per-instance scoping resolves this. Probe-02 launches two `KittySession`s in parallel (the existing harness already supports this) and confirms each gets its own socket. |
| macOS `/tmp` symlink behaviour breaks the socket on resolve | Kitty resolves the path itself; the symlink is transparent. Repro on a macOS host (deferred if no host) verifies. Until verified, the `## macOS Status` section of the repro doc carries `deferred-with-reason`. |
| Stale socket files from a crashed kitty linger in `/tmp` | Kitty unlinks the socket on `os_window` exit when shutting down cleanly. On crash, a stale file remains; the next kitty with the same PID (rare but possible after PID wraparound) would fail to listen. Mitigation: `my-kitty doctor` already runs `kitty @ ls` against the socket — a stale-file mismatch surfaces there with a clear error. No automatic cleanup; manual `rm /tmp/kitty-*` is documented in the repro doc as the remediation. |
| User has their own `kitty.conf` directive that overrides our `allow_remote_control` | The sentinel-bracketed include is at the bottom of `kitty.conf` per `kitty-config-management`, so our value wins. If the user manually re-orders the include block, they get to keep both pieces; `my-kitty doctor` surfaces the discrepancy via the reachability check failing. |
| RC enables actions the user did not anticipate (e.g. another process sending keystrokes) | D2 records the trade-off. Single-user host = realistic threat is low. The doctor failure mode + the verbose `WHY` block at the top of `remote-control.conf` document the posture so it is opt-out-able by removing the include. |
| Adding a doctor check changes its exit-code shape for users who script around doctor's output | The new check follows the same `PASS|FAIL|SKIP <name>: <detail>` line format as the other six. `SKIP` is new but is non-failing (exit 0 still possible). Documented in the modified `kitty-install` requirement scenarios. |

## Migration Plan

1. Probe first (`tmp/h21-*`), then promote: per the project's hypothesis-before-implementation rule. No `config/kitty/remote-control.conf` lands in `config/` until h21 is green on Linux.
2. Land the `.conf` file, include line, doctor check, and integration test in one commit. Surgical install/uninstall handles propagation automatically.
3. macOS verification: deferred-with-reason in the repro doc if no host is accessible at apply time. The follow-up tracking line goes into `verification.md` (suggested name: `phase2-remote-control-foundation-macos`).
4. Rollback: removing `include remote-control.conf` from `kitty-setup.conf` and re-running `make setup` reverts the surface in full. The `.conf` file alone is inert without the include.

## Open Questions

- **OQ-1 (RESOLVED, 2026-05-12):** Does kitty 0.46.x expand `$KITTY_PID` literally inside `listen_on` value? **No** — probe 01 confirms the literal string is not substituted. Kitty auto-appends `-<PID>` instead. Design adjusted to `listen_on unix:/tmp/kitty`.
- **OQ-2:** On macOS Sequoia (15.x), do sandbox restrictions on `/tmp` block unix-socket creation? Resolved by probe 05 on a macOS host (currently deferred-with-reason).
- **OQ-3:** Should `my-kitty doctor` enumerate every running kitty (including ones not started from the managed config — e.g. an old kitty the user launched before `make setup`) or only those whose env points at our config? D3 picks "every running kitty" as it is simpler and surfaces drift; revisit if it produces noise.

## Probes

External-system evidence per R6. Each row: probe ID, assumption summary, verdict, design decision it informs.

| ID | Assumption | Verdict | Used by |
|---|---|---|---|
| 01 | `$KITTY_PID` expands inside `listen_on` value | `partial-with-workaround` (assumption falsified; workaround: drop placeholder, rely on kitty's auto-`-<PID>` suffix) | D1 — corrects the `listen_on` value to `unix:/tmp/kitty`. Resolves OQ-1. Spec scenario "Ship a remote-control include file" + "expose a per-instance unix socket". |
| 02 | Two concurrent kitty instances get distinct, non-colliding sockets and each `kitten @` call sees only its instance | `holds` | D1 risk row "two concurrent instances". Spec scenario "Two concurrent instances each have their own socket". |
| 03 | Kitty creates the socket with mode `0600` | `partial-with-workaround` (actual mode is umask-determined; observed `0775` under shell umask `0022`. Access scoping is by UID via the kernel UDS check, not by `0600` file mode) | D1 + D2 (security trade-off). Spec scenario "Socket permission scoping" — wording revised to drop literal `0600`. |
| 04 | A shell with `KITTY_LISTEN_ON` unset can call `kitten @ --to unix:/tmp/kitty-<PID> ls` and receive valid JSON | `holds` | Spec scenario "Out-of-process call reaches the socket" (load-bearing). D4 probe shape. Doctor's `check_remote_control_reachable()` uses the same call. |
| 05 | macOS `/tmp` symlink does not break the socket path; kitty 0.46.x on macOS Sequoia behaves identically to Linux | `deferred-with-reason` (no macOS host accessible) | D1 cross-platform claim. Spec scenario "macOS is deferred". Follow-up change: `phase2-remote-control-foundation-macos`. |

Probe artefacts under `tmp/probes/phase2-remote-control-foundation/01..05-*.md` (gitignored; deleted at archive time per R6 once findings are encoded in this section and in commit messages).
