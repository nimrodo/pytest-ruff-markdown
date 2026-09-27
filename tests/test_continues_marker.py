"""Opt-in annotation: `<!-- pytest-ruff-markdown: continues -->` immediately
above a fenced Python block lints that Block with the source of all preceding
*consecutive* `continues`-marked Blocks prepended as context, so a later Block
can reference a name/import established in an earlier one without tripping
`F821`/`F401`.

Uses runpytest_subprocess() for the same reason as tests/test_lint.py: .md
collection only happens via the real pytest11 entry point.
"""


def test_continues_block_sees_preceding_blocks_import(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

```python
import sys
```

<!-- pytest-ruff-markdown: continues -->
```python
print(sys.path)
```
""",
    )

    result = pytester.runpytest_subprocess("-v")

    # The root block is still linted in isolation and unaffected: `sys` is
    # unused *within it alone*, so it still fails on its own.
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["FAILED example.md::L4*"])
    result.stdout.fnmatch_lines(["*example.md:4:*F401*"])
    result.stdout.fnmatch_lines(["example.md::L9 PASSED*"])


def test_chain_is_cumulative_and_transitive(pytester):
    pytester.makefile(
        ".md",
        example="""\
```python
import sys
```

<!-- pytest-ruff-markdown: continues -->
```python
value = sys.path
```

<!-- pytest-ruff-markdown: continues -->
```python
print(value)
```
""",
    )

    result = pytester.runpytest_subprocess()

    # The third block needs visibility into both the first (`sys`) and the
    # second (`value`), not just the immediately preceding one.
    result.assert_outcomes(passed=2, failed=1)


def test_violation_in_prepended_context_not_reattributed_to_continues_block(
    pytester,
):
    pytester.makefile(
        ".md",
        example="""\
```python
import sys
import os
```

<!-- pytest-ruff-markdown: continues -->
```python
os.getcwd()
```
""",
    )

    result = pytester.runpytest_subprocess("-v")

    # `sys`/`os` are unused *within the root block alone* -- that's the
    # root's own isolated result and must not affect the continues block,
    # which does use `os` once the chain's context is included.
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["FAILED example.md::L2*"])
    result.stdout.fnmatch_lines(["example.md::L8 PASSED*"])


def test_continues_marker_on_first_block_fails_collection(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

<!-- pytest-ruff-markdown: continues -->
```python
x = 1
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*continues*"])
    result.stdout.fnmatch_lines(["*no preceding Block*"])


def test_marker_not_immediately_before_fence_is_ignored(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

```python
x = 1
```

<!-- pytest-ruff-markdown: continues -->

```python
print(x)
```
""",
    )

    result = pytester.runpytest_subprocess()

    # The blank line between the marker and the fence means the marker
    # doesn't apply: the second block is linted in isolation and `x` is
    # undefined there.
    result.assert_outcomes(passed=1, failed=1)


def test_unmarked_blocks_are_entirely_unaffected(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

```python
x = 1
```

```python
import sys
```

```python
y = 2
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=2, failed=1)
