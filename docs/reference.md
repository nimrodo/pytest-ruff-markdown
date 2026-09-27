# Reference

Exhaustive reference for `pytest-ruff-markdown`'s markers, filename contract,
and CLI. For installation and a quickstart, see the [README](../README.md).

## Collection

Each ` ```python `/` ```py ` fenced block in a collected `.md` file becomes
its own `pytest` item. Every block is linted **in isolation**: it has no
visibility into any other block in the same document, or into surrounding
prose. A block can opt out of isolation for its preceding chain with the
[continues marker](#continues-marker).

## Markers

### Skip marker

```
<!-- pytest-ruff-markdown: skip -->
```

Placed immediately above a fence. Excludes that block from linting: the
pytest item still exists and is reported, but as skipped.

### Continues marker

```
<!-- pytest-ruff-markdown: continues -->
```

Placed immediately above a fence. Opts that block into being linted with the
source of all preceding *consecutive* `continues`-marked blocks prepended as
context (walking backward until a block without the marker), so it no longer
fails `F821`/`F401` for names/imports established there.

- Chaining is cumulative and transitive: a third block that `continues` from
  a second block that itself `continues` from a first sees all three
  blocks' source.
- Each block in a chain is still collected and reported as its own
  independent pytest item.
- A violation located in the *prepended* context is attributed to the block
  that introduced it, not to the block continuing from it.
- A `continues` marker on a file's first block (nothing to continue from) is
  a collection error, not a silent no-op.

## Synthetic filenames

Each block is piped into `ruff` under a synthetic filename of the form
`{markdown-stem}__block{N}.py`, resolved inside the same real directory as
the source Markdown file (e.g. `docs/tutorial.md`'s second block becomes
`docs/tutorial__block2.py`).

This is a stable contract you can target with your own `ruff`
[`per-file-ignores`](https://docs.astral.sh/ruff/settings/#lint_per-file-ignores)
config to scope any other rule (import sorting, `B018`, etc.) for embedded
code, without any plugin-specific configuration:

```toml
[tool.ruff.lint.per-file-ignores]
"docs/*.py" = ["I001"]
```

## Suppressed rules

**`D100` (missing module docstring) is always ignored.** A block a few
lines long structurally cannot have a module docstring, so this plugin
suppresses `D100` unconditionally, regardless of whether your own `ruff`
config selects `D`. Other `D` rules (e.g. `D103` on an undocumented
function) are unaffected and still fire normally.

## `pytest-ruff-markdown-format` CLI

`ruff check` (linting) runs as part of the pytest suite, but `ruff format`
is a mutation, not a check, so it doesn't fit as a pytest item. Instead, a
separate console script reformats blocks in place:

```
uv run pytest-ruff-markdown-format docs/tutorial.md
```

- Accepts one or more files or directories. Directories are searched
  recursively for `.md` files.
- A block marked with the [skip marker](#skip-marker) is left untouched.
- `--check`: exit nonzero if anything needs reformatting, without writing.
- `--diff`: same as `--check`, but also print a unified diff.

These flags mirror `ruff format --check`/`--diff` itself, and are intended
for CI:

```
uv run pytest-ruff-markdown-format --check docs/
```
