# pytest-ruff-markdown

A pytest plugin that lints ```python``` / ```py``` fenced code blocks in Markdown files with [ruff](https://docs.astral.sh/ruff/). Each fenced block in a collected `.md` file becomes its own pytest item.

## Installation

Add it as a dev dependency in your project:

```
uv add --dev pytest-ruff-markdown
```

## Usage notes

Each fenced block is linted as its own isolated file — it has no visibility
into any other block in the same document, or into surrounding prose. Two
consequences of that:

- **`D100` (missing module docstring) is always ignored.** A block a few
  lines long structurally cannot have a module docstring, so this plugin
  suppresses `D100` unconditionally, regardless of whether your own `ruff`
  config selects `D`. Other `D` rules (e.g. `D103` on an undocumented
  function) are unaffected and still fire normally.
- **`F821`/`F401` can fire on names or imports that are actually defined in
  a different block, or in the surrounding prose** (for example, a class
  split across two fences). This is intentional: isolated linting is what
  gives each block its own pass/fail and its own line number, and these
  codes are the plugin's main value. If a specific block is a legitimately
  fragmentary example, opt it out with:

  ```
  <!-- pytest-ruff-markdown: skip -->
  ```

  placed immediately above the fence.

  For genuinely sequential, tutorial-style docs (step 2 builds on step 1),
  you can instead opt a block into sharing the preceding block's source as
  context, with:

  ```
  <!-- pytest-ruff-markdown: continues -->
  ```

  placed immediately above the fence. The marked block is linted alongside
  the source of all preceding *consecutive* `continues`-marked blocks
  (walking backward until a block without the marker), so it no longer
  fails `F821`/`F401` for names/imports established there. Chaining is
  cumulative: a third block that `continues` from a second block that
  itself `continues` from a first sees all three blocks' source. Each
  block is still collected and reported as its own independent pytest
  item, and a violation located in the *prepended* context is attributed
  to the block that introduced it, not to the block continuing from it. A
  `continues` marker on a file's first block (nothing to continue from) is
  a collection error, not a silent no-op.

Each block is piped into `ruff` under a synthetic filename of the form
`{markdown-stem}__block{N}.py`, resolved inside the same real directory as
the source Markdown file (e.g. `docs/tutorial.md`'s second block becomes
`docs/tutorial__block2.py`). This is a stable contract you can target with
your own `ruff` [`per-file-ignores`](https://docs.astral.sh/ruff/settings/#lint_per-file-ignores)
config to scope any other rule (import sorting, `B018`, etc.) for embedded
code, without any plugin-specific configuration:

```toml
[tool.ruff.lint.per-file-ignores]
"docs/*.py" = ["I001"]
```

## Formatting blocks

`ruff check` (linting) runs as part of the pytest suite, but `ruff format`
is a mutation, not a check, so it doesn't fit as a pytest item. Instead, a
separate console script reformats blocks in place:

```
uv run pytest-ruff-markdown-format docs/tutorial.md
```

Pass one or more files or directories (directories are searched recursively
for `.md` files). Blocks marked with the Skip Marker are left untouched.
For CI, use `--check` (exit nonzero if anything needs reformatting, without
writing) or `--diff` (same, but also print a unified diff), mirroring
`ruff format --check`/`--diff` itself:

```
uv run pytest-ruff-markdown-format --check docs/
```
