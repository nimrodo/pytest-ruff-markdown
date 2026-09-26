"""Core lint behavior: zero-config collection of fenced Python blocks in
markdown, one pytest item per block, ruff-backed pass/fail reported against
the original markdown line.

Uses runpytest_subprocess() throughout (not runpytest()/runpytest_inprocess())
because collection of ``.md`` files only happens once pytest boots via the
real pytest11 entry point (see tests/test_plugin_entry_point.py and ticket #5).
"""


def test_single_valid_python_block_passes(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

```python
x = 1
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)


def test_invalid_block_reports_original_markdown_line(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

```python
x = 1
```

Some prose in between that pushes the next block further down the file, so
the violation below is nowhere near line 1.

```python
import sys
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["FAILED example.md::L11*"])
    result.stdout.fnmatch_lines(["*example.md:11:*F401*"])


def test_bare_and_non_python_fences_are_not_collected(pytester):
    pytester.makefile(
        ".md",
        example="""\
# Doc

```
not_python = "bare fence, ignored"
```

```javascript
console.log("also ignored");
```

```python
x = 1
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)


def test_multiple_blocks_are_independent_items(pytester):
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
