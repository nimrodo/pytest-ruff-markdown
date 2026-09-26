# Contributing

## Validating against a local checkout

To manually check the plugin against a real project without adding it as a dependency, run it from your checkout with `uv run --with`:

```
uv run --with pytest-ruff-markdown@/path/to/pytest-ruff-markdown python -m pytest
```

**Invoke pytest via `python -m pytest`, not the bare `pytest` command.** Bare `pytest` can resolve to a pre-existing `pytest` executable outside the ephemeral overlay environment (for example, the target project's own `.venv/bin/pytest`) that does not have this plugin installed. When that happens it fails silently: no error, just zero `.md` files collected, or a confusing `ERROR: not found: .../README.md (no match in any of [...])` if you point it at a markdown file directly. `python -m pytest` runs pytest from the interpreter `uv run` just resolved, which guarantees it is the one with the plugin installed.

### Troubleshooting

Not collecting `.md` files? Confirm the plugin is actually registered:

```
uv run --with pytest-ruff-markdown@/path/to/pytest-ruff-markdown python -m pytest --trace-config | grep ruff_markdown
```

If nothing prints, pytest is running from an environment without the plugin installed — check which `pytest`/`python` you're invoking.
