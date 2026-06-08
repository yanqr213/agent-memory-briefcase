# Contributing

Thanks for helping improve `agent-memory-briefcase`.

## Development setup

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Project conventions

- Keep runtime dependencies at zero unless a strong justification exists.
- Prefer standard library modules.
- Preserve local-first behavior and do not introduce LLM API calls.
- Keep every durable memory artifact versionable as Markdown or JSON.
- Add or update tests with each behavior change.

## Release checklist

1. Update `CHANGELOG.md`.
2. Run `python -m unittest discover -s tests -v`.
3. Run `python -m agent_memory_briefcase check --root examples/demo_bundle --check warning`.
4. Build distributions with `python -m build`.

## Issue reports

When reporting a bug, include:

- Python version
- platform
- command line used
- expected result
- actual result
- whether the bundle was newly initialized or pre-existing

