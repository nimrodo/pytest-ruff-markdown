# pytest-ruff-markdown

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A pytest plugin that lints ```python``` / ```py``` fenced code blocks in Markdown files with [ruff](https://docs.astral.sh/ruff/). Each fenced block in a collected `.md` file becomes its own pytest item.

## Installation

Add it as a dev dependency in your project:

```
uv add --dev pytest-ruff-markdown
```

## Usage notes

Each fenced block is linted as its own isolated file — it has no visibility
into any other block in the same document, or into surrounding prose. That
means `F821`/`F401` can fire on names or imports that are actually defined
in a different block (for example, a class split across two fences). This
is intentional: isolated linting is what gives each block its own
pass/fail and its own line number, and it's the plugin's main value. A
block can opt out of linting entirely with a skip marker, or opt into
sharing a preceding block's source as context with a continues marker:

```
<!-- pytest-ruff-markdown: skip -->
```

```
<!-- pytest-ruff-markdown: continues -->
```

Formatting (`ruff format`) is a mutation, not a check, so it runs via a
separate console script instead of as a pytest item:

```
uv run pytest-ruff-markdown-format docs/tutorial.md
```

See [the reference docs](docs/reference.md) for full details on the
markers, the synthetic filename contract for scoping your own `ruff`
config, the `D100` suppression, and the `pytest-ruff-markdown-format` CLI
flags.
