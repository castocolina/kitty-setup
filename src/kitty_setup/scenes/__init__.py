"""Runtime scene primitives — Phase 2 §8-§14 (see docs/requirements.md)."""

# Expose `scenes.title` as a module attribute so `cli.scenes.title` resolves
# for monkeypatch.setattr in tests/unit/test_cli.py (§6.5–6.6 of
# phase2-scene-title-primitive tasks).
from kitty_setup.scenes import title  # noqa: F401
