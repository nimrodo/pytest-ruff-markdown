"""Opt-out annotation: `<!-- pytest-ruff-markdown: skip -->` immediately above
a fenced Python block excludes it from ruff linting while still collecting it
as a (skipped) pytest item.

Uses runpytest_subprocess() for the same reason as tests/test_lint.py: .md
collection only happens via the real pytest11 entry point.
"""


def test_marked_block_is_skipped_not_failed(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

<!-- pytest-ruff-markdown: skip -->
```python
import sys
```
""",
    )

    result = pytester.runpytest_subprocess("-v")

    result.assert_outcomes(skipped=1)
    result.stdout.fnmatch_lines(["*pytest-ruff-markdown: skip*"])


def test_only_marked_block_is_skipped_others_lint_normally(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

```python
x = 1
```

<!-- pytest-ruff-markdown: skip -->
```python
import sys
```

```python
y = 2
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=2, skipped=1)


def test_marker_line_itself_does_not_break_other_blocks_line_accuracy(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

<!-- pytest-ruff-markdown: skip -->
```python
import sys
```

Some prose in between that pushes the next block further down the file, so
the violation below is nowhere near line 1.

```python
import os
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(skipped=1, failed=1)
    result.stdout.fnmatch_lines(["FAILED example.md::L12*"])
    result.stdout.fnmatch_lines(["*example.md:12:*F401*"])


def test_marker_not_immediately_before_fence_is_ignored(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

<!-- pytest-ruff-markdown: skip -->

```python
import sys
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(failed=1)
