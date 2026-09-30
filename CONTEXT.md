# pytest-ruff-markdown

A pytest plugin that treats fenced Python code samples inside Markdown files as lintable units, checking each one with `ruff` and reporting failures against the original Markdown file's line numbers.

## Language

**Block**:
A single ` ```python `/` ```py ` fenced code sample extracted from a Markdown file. The block is the atomic unit of collection and linting — one `pytest` item per block.
_Avoid_: snippet, fence, code sample (as a synonym for the collected/linted unit)

**Isolated linting**:
The model where each block is linted entirely on its own, with no visibility into any other block in the same file or any surrounding prose. This is the plugin's default for every block; a block can opt out of it for its preceding chain via the Continues Marker.
_Avoid_: standalone linting, per-snippet linting

**Synthetic filename**:
The `{markdown-stem}__block{N}.py` path a block is given when piped into `ruff` via `--stdin-filename`. Always resolved inside the same real directory as the source Markdown file. This is a stable, documented contract: a user can target it with their own `ruff` `per-file-ignores` config to scope rules for embedded blocks without any plugin-specific configuration.
_Avoid_: virtual filename, stdin filename (as the user-facing term — that's the flag name, not the concept)

**Skip marker**:
The `<!-- pytest-ruff-markdown: skip -->` HTML comment placed immediately above a fence. Excludes that one block from linting entirely (the pytest item still exists and is reported, but as skipped). The sanctioned way to opt a specific, legitimately-fragmentary example out of checking.
_Avoid_: ignore marker, exclude comment

**Continues marker**:
The `<!-- pytest-ruff-markdown: continues -->` HTML comment placed immediately above a fence. Opts that block into being linted with the source of all preceding *consecutive* continues-marked blocks prepended as context (walking backward to the nearest block without the marker), so it can reference a name/import established there without a false-positive `F821`/`F401`. Chaining is cumulative and transitive; each block in a chain is still collected and reported as its own independent pytest item, and a violation in the prepended context is attributed to the block that introduced it, never to the block continuing from it. The formatter treats a chain the same way: the chain's Blocks are formatted together as one unit, so a fragment valid only in context (an indented method body) formats cleanly, while each Block's own lines are rewritten and Skip-Marked Blocks are context only. A `continues` Block sees only the chain it declares; isolation stays the default. A marker on a file's first block (no preceding block to continue from) is a collection error.
_Avoid_: continuation marker, chain marker (as the user-facing term — "continues" is the marker's literal keyword)
