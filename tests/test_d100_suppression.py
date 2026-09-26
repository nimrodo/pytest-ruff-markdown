"""D100 (missing module docstring) is a category error against a Block: a
fenced snippet a few lines long structurally cannot have a module docstring,
so it is unconditionally suppressed regardless of the user's own `ruff`
`select` config. Other `D` rules (e.g. D103) and cross-block F821/F401 are
unaffected. See docs/adr/0001-isolated-block-linting-semantics.md.

Uses runpytest_subprocess() for the same reason as tests/test_lint.py: .md
collection only happens via the real pytest11 entry point.
"""


def test_block_with_only_missing_docstring_passes_even_with_d_selected(pytester):
    pytester.makepyprojecttoml(
        """\
[tool.ruff.lint]
select = ["D"]
"""
    )
    pytester.makefile(
        ".md",
        example="""\
# Doc

```python
def documented():
    \"\"\"Do the thing.\"\"\"
    return 1
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)


def test_other_docstring_rules_still_fire_with_d_selected(pytester):
    pytester.makepyprojecttoml(
        """\
[tool.ruff.lint]
select = ["D"]
"""
    )
    pytester.makefile(
        ".md",
        example="""\
# Doc

```python
def undocumented():
    return 1
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*D103*"])


def test_cross_block_names_still_fire_with_d_selected(pytester):
    pytester.makepyprojecttoml(
        """\
[tool.ruff.lint]
select = ["D", "F"]
"""
    )
    pytester.makefile(
        ".md",
        example="""\
# Doc

```python
import sys
```

```python
sys.exit()
```
""",
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(failed=2)
    result.stdout.fnmatch_lines(["*F401*"])
    result.stdout.fnmatch_lines(["*F821*"])
