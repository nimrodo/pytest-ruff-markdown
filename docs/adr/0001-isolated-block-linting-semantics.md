# Isolated block linting: keep it, plus its two exceptions

We lint each fenced code Block independently, with no shared scope across Blocks in the same file. This was reconsidered while investigating near-100% false positives against a real project's docs (issue #17) and kept deliberately, because whole-file concatenation trades one false-positive class (cross-block `F821` on names defined in an earlier block) for a different one (cross-example `F811` redefinition collisions, when two unrelated examples happen to reuse the same name), while also losing the per-block failure granularity (`file.md::L36`) that isolated linting gives for free.

Two rules get special treatment within that isolated model, both decided the same session:

- **`D100` (missing module docstring) is unconditionally suppressed** via `--extend-ignore D100` on every `ruff` invocation, regardless of the user's own `ruff` config selecting `D`. This is not a style override: a Block structurally cannot have a module docstring in any meaningful sense, so enforcing `D100` against one is a category error, not a legitimate lint.
- **`F821`/`F401` are deliberately left as real findings by default**, even though isolated linting means they sometimes fire on a name/import that's actually defined in a different Block or in surrounding prose. These codes are also the plugin's core value (catching genuinely undefined names and unused imports within a Block), so silencing them by default would throw out real bug-catching along with the false positives. The Skip Marker is the sanctioned per-block escape hatch for authors who know a specific example is intentionally fragmentary.

## Considered and rejected

A bespoke plugin-specific config surface for scoping rules per block/file was considered and rejected: `ruff`'s own `per-file-ignores` already works today against the Synthetic Filename convention (confirmed empirically — the filename is stable and always resolves inside the real Markdown file's directory), so a user can already scope out `I001`, `B018`, or anything else for their own docs without any plugin-specific mechanism. Building a second config system would duplicate what `ruff` already provides.
