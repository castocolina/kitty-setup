"""Runtime scene primitives — Phase 2 §8-§14 (see docs/requirements.md)."""

# Expose each scene module as a `scenes.<name>` attribute so `cli.scenes.<name>`
# resolves for `monkeypatch.setattr` targets in tests/unit/test_cli.py.
from kitty_setup.scenes import accent, background, font, opacity, title  # noqa: F401
