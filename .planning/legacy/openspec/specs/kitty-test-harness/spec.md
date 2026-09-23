# kitty-test-harness Specification

## Purpose
TBD - created by archiving change bootstrap-foundation-phase1-popos. Update Purpose after archive.
## Requirements
### Requirement: Spawn an isolated kitty session per test

The system SHALL provide a `KittySession` Python context manager that spawns a kitty process with a per-session socket (`tmp/sessions/<id>/sock`), a per-session config directory (`tmp/sessions/<id>/conf`), `--start-as=minimized`, and remote control enabled via `-o allow_remote_control=yes --listen-on=unix:tmp/sessions/<id>/sock`. The session MUST NOT read the user's `~/.config/kitty/` and MUST NOT write outside its own session directory.

#### Scenario: Two sessions can run concurrently
- **WHEN** two `KittySession` instances are entered in parallel from the same test process
- **THEN** each spawns a distinct kitty process with a distinct socket path, and `kitty @ ls` against each socket returns only that session's tabs and windows

#### Scenario: Session ignores user config
- **WHEN** the user has bindings in `~/.config/kitty/kitty.conf` that conflict with the test
- **THEN** those bindings have no effect inside the session, because the session's `--config` argument points at a session-local file
- **AND** the test reading `KittySession.ls()` sees only test-supplied state

### Requirement: Wait for the remote-control socket to be ready

The system SHALL poll the session's Unix socket via `kitty @ --to unix:<path> ls` until the call returns successfully, with a maximum wait of 5 seconds. If the socket is not ready within that window, the system MUST kill the kitty process and raise a `HarnessStartupError` describing the failure (last stderr from kitty, last error from `kitty @`, elapsed wait).

#### Scenario: Socket becomes ready quickly
- **WHEN** the session is entered on a healthy host
- **THEN** the context manager returns control to the caller within the 5-second window and `KittySession.ls()` returns valid JSON

#### Scenario: Socket never becomes ready
- **WHEN** the kitty binary is missing or the spawn fails silently
- **THEN** the context manager raises `HarnessStartupError` with the captured kitty log content, and no kitty process is left running on the host

### Requirement: Provide remote-control method wrappers

The system SHALL expose, on `KittySession`, the following methods that wrap `kitty @` calls and raise `HarnessCommandError` on non-zero exit: `ls() -> dict`, `send_key(keys: str) -> None`, `send_text(text: str) -> None`, `launch(**kwargs) -> dict`, `get_text(extent: str = "all") -> str`. Each method MUST direct its call at the session's own socket and MUST NOT rely on environment variables.

#### Scenario: Sending text appears in get_text
- **WHEN** the test calls `session.send_text("hello")` followed by `session.get_text(extent="all")`
- **THEN** the returned text contains `"hello"`

#### Scenario: A failed remote-control call surfaces the error
- **WHEN** the test calls `session.launch(type="invalid-window-type")`
- **THEN** the call raises `HarnessCommandError` containing the kitty `@`-side stderr

### Requirement: Deterministic teardown

On context exit (normal or exception), the system SHALL send `kitty @ close-os-window --match all` to the session, wait up to 2 seconds for the kitty process to exit, then SIGTERM, then SIGKILL after 5 more seconds. The session directory SHALL be deleted on success, kept on failure (with the last `actual.json` and `kitty.log` intact for inspection). When `KEEP_SESSIONS=1` is set in the environment, the session directory MUST be kept regardless of outcome.

#### Scenario: Successful test cleans up
- **WHEN** the context manager exits without an exception
- **THEN** the session's kitty process is gone, the session socket file is gone, and the session directory has been removed

#### Scenario: Failing test preserves evidence
- **WHEN** the context manager exits with an exception
- **THEN** the session's kitty process is gone, but the session directory (with `kitty.log` and any captured outputs) remains at `tmp/sessions/<id>/` for inspection

### Requirement: Integration tests are gated by an opt-in environment variable

The system SHALL skip all integration tests under `tests/integration/` unless the environment variable `KITTI_INTEGRATION` is set to `1`. Unit tests under `tests/unit/` MUST run unconditionally.

#### Scenario: Local default skips integration
- **WHEN** the developer runs `uv run pytest tests/` without setting `KITTI_INTEGRATION`
- **THEN** the integration tests are reported as skipped, and the test run still exits 0 if unit tests pass

#### Scenario: Opt-in runs integration
- **WHEN** the developer runs `KITTI_INTEGRATION=1 uv run pytest tests/`
- **THEN** the integration tests execute against real kitty sessions

