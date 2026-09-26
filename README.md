# pytest-ruff-markdown

A pytest plugin that lints ```python``` / ```py``` fenced code blocks in Markdown files with [ruff](https://docs.astral.sh/ruff/). Each fenced block in a collected `.md` file becomes its own pytest item.

## Installation

Add it as a dev dependency in your project:

```
uv add --dev pytest-ruff-markdown
```

### Ephemeral install (no repo changes)

To try the plugin against a project without adding it as a dependency, use `uv run --with`. **Invoke pytest via `python -m pytest`, not the bare `pytest` command:**

```
uv run --with pytest-ruff-markdown python -m pytest
```

Bare `pytest` can resolve to a pre-existing `pytest` executable outside the ephemeral overlay environment (for example, the target project's own `.venv/bin/pytest`) that doesn't have this plugin installed. When that happens it fails silently: no error, just zero `.md` files collected, or a confusing `ERROR: not found: .../README.md (no match in any of [...])` if you point it at a markdown file directly. `python -m pytest` runs pytest from the interpreter `uv run` just resolved, which guarantees it's the one with the plugin installed.

### Troubleshooting

Not collecting `.md` files? Confirm the plugin is actually registered:

```
uv run --with pytest-ruff-markdown python -m pytest --trace-config | grep ruff_markdown
```

If nothing prints, pytest is running from an environment without the plugin installed — check which `pytest`/`python` you're invoking.
