"""The Synthetic Filename (`{markdown-stem}__block{N}.py`, resolved inside
the same real directory as the source Markdown file) is a stable contract: a
user can target it with their own `ruff` `per-file-ignores` config to scope
rules for embedded Blocks, with no plugin-specific configuration. See
docs/adr/0001-isolated-block-linting-semantics.md.

Uses runpytest_subprocess() for the same reason as tests/test_lint.py: .md
collection only happens via the real pytest11 entry point.
"""


def test_per_file_ignores_targeting_markdown_directory_scopes_a_rule(pytester):
    pytester.makepyprojecttoml(
        """\
[tool.ruff.lint]
select = ["I"]

[tool.ruff.lint.per-file-ignores]
"docs/*.py" = ["I001"]
"""
    )
    docs_dir = pytester.mkdir("docs")
    (docs_dir / "example.md").write_text(
        """\
# Doc

```python
import sys
import os
```
""",
        encoding="utf-8",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)


def test_per_file_ignores_does_not_leak_across_directories(pytester):
    pytester.makepyprojecttoml(
        """\
[tool.ruff.lint]
select = ["I"]

[tool.ruff.lint.per-file-ignores]
"docs/*.py" = ["I001"]
"""
    )
    other_dir = pytester.mkdir("other")
    (other_dir / "example.md").write_text(
        """\
# Doc

```python
import sys
import os
```
""",
        encoding="utf-8",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*I001*"])
