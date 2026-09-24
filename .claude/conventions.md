# Language & Tooling Conventions — Python (current)

This file is the **plug point** for stack-specific rules. To switch the project to a
different language, replace the contents of this file with the new stack's conventions.
The filename (`.claude/conventions.md`) and the link from `AGENTS.md` stay the same.

Applies whenever the repo contains Python source. Phase 1 (foundation) may ship without
Python — these rules engage as soon as a `pyproject.toml` lands.

## Runtime & dependencies

- Python 3.12+, managed via [uv](https://github.com/astral-sh/uv) (`~/.local/bin/uv`).
- Always invoke through `uv run python` or `.venv/bin/python` — never raw `python` / `python3`.
- Dependencies are added with `uv add` followed by `uv sync`. Never `pip install`.
- Always execute from the project root, never from inside `src/`.
- No conditional imports. The single allowed exception is `if TYPE_CHECKING:` for type hints.

## Type system & code design

- Type hints on every function, method, and class attribute.
- Pyright strict mode is enforced — code must pass without suppressions.
- Never silence findings with `# noqa`, `# type: ignore`, `# pylint: disable`, etc. Fix the
  root cause; if a tool is wrong, configure it explicitly with rationale in the config file.
- Prefer classes with behavior over standalone functions when state or coordination is
  involved.
- Prefer `dataclass` / pydantic models over raw dicts and tuples for structured data.
- Prefer `enum.Enum` / `enum.StrEnum` over string constants for closed option sets.
- Pydantic is the default for integration boundaries (external configs, TOML scenes,
  `kitty @` payloads).

## Code quality tooling

The pipeline (added with the first Python module) is:

| Tool    | Role                              | Config              |
|---------|-----------------------------------|---------------------|
| black   | canonical formatter, 100 cols     | `pyproject.toml`    |
| ruff    | lint-only (no formatting), 100 c. | `pyproject.toml`    |
| pyright | strict type checking              | `pyproject.toml`    |
| bandit  | security lint                     | `pyproject.toml` (read only via `-c pyproject.toml`) |
| vulture | dead-code detection               | `vulture_allowlist` |
| pytest  | tests + coverage                  | `pyproject.toml`    |

`black` is the single source of truth for formatting; `ruff format` is intentionally not in the
chain. The `vulture_allowlist.py` is reserved for *near-term* public APIs with a referenced
task ID — never a dumping ground.

### Targeted single-file commands

```bash
uv run black <file>
uv run ruff check <file> --fix
uv run pyright <file>
uv run bandit -c pyproject.toml -q -r <path>
uv run vulture src tests vulture_allowlist.py
uv run pytest tests/unit/test_<module>.py
```

### Make targets (when Makefile exists)

```bash
make format            # black + ruff --fix on src/ and tests/
make validate          # full pre-commit pipeline
make test              # pytest with coverage
make test-unit
make test-integration  # tests/integration headless under a nested compositor (cage); fails loudly without one
```

Never commit code that fails `make validate`.

## Testing

- `tests/unit/` — fast, isolated, Kitty mocked.
- `tests/integration/` — real Kitty session when available.
- TDD is the default for new modules: write a failing test first, then implement.
- Coverage floor: ≥80% once the test suite exists.
