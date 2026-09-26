# pytest-ruff-markdown

A pytest plugin that treats fenced Python code samples inside Markdown files as lintable units, checking each one with `ruff` and reporting failures against the original Markdown file's line numbers.

## Language

**Block**:
A single ` ```python `/` ```py ` fenced code sample extracted from a Markdown file. The block is the atomic unit of collection and linting — one `pytest` item per block.
_Avoid_: snippet, fence, code sample (as a synonym for the collected/linted unit)

**Isolated linting**:
The model where each block is linted entirely on its own, with no visibility into any other block in the same file or any surrounding prose. This is the plugin's default and only linting model.
_Avoid_: standalone linting, per-snippet linting

**Synthetic filename**:
The `{markdown-stem}__block{N}.py` path a block is given when piped into `ruff` via `--stdin-filename`. Always resolved inside the same real directory as the source Markdown file. This is a stable, documented contract: a user can target it with their own `ruff` `per-file-ignores` config to scope rules for embedded blocks without any plugin-specific configuration.
_Avoid_: virtual filename, stdin filename (as the user-facing term — that's the flag name, not the concept)

**Skip marker**:
The `<!-- pytest-ruff-markdown: skip -->` HTML comment placed immediately above a fence. Excludes that one block from linting entirely (the pytest item still exists and is reported, but as skipped). The sanctioned way to opt a specific, legitimately-fragmentary example out of checking.
_Avoid_: ignore marker, exclude comment
