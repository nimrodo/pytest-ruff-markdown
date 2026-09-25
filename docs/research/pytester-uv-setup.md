# Configuring `pytester` for a `uv` src-layout plugin project

Research for [#5](https://github.com/nimrodo/pytest-ruff-markdown/issues/5) (child of map issue #2).

## 1. Enabling the `pytester` fixture

`pytester` ships inside pytest itself but is **disabled by default**, exactly like `pytester`'s
legacy alias `testdir`. There are two ways to turn it on, both documented on pytest's
["Testing plugins"](https://docs.pytest.org/en/stable/how-to/writing_plugins.html#testing-plugins)
page:

1. **`pytest_plugins = ["pytester"]`** declared in a **top-level (rootdir) `conftest.py`.**
   This activates the fixture for the whole test session.
2. **`-p pytester`** passed on the command line (or added to `addopts`), as a one-off opt-in.

Important scoping caveat, confirmed in pytest's own
[deprecations page](https://docs.pytest.org/en/stable/deprecations.html): declaring
`pytest_plugins` in a **non-root** `conftest.py` was deprecated and then **removed in pytest
4.0**, because it would activate the plugin globally in a way that's inconsistent with how
`conftest.py` files are normally scoped (active only at-or-below their directory). So
`pytest_plugins = ["pytester"]` **must** live in the `conftest.py` at the repo root (the pytest
rootdir), not in a nested `tests/subdir/conftest.py`.

In practice, real plugins (e.g. `pytest-mock`) put the declaration directly at the top of their
test module instead of a conftest — pytest still honours `pytest_plugins` set at the top of a
top-level test file, but **`conftest.py` at the repo root is the documented, non-deprecated
mechanism** and is what should be used here.

### Interaction with `pyproject.toml`'s `[tool.pytest.ini_options]`

`[tool.pytest.ini_options]` and `pytest_plugins` are orthogonal knobs — no direct interaction:

- `[tool.pytest.ini_options]` in `pyproject.toml` sets ini-style options (`addopts`, `testpaths`,
  `markers`, etc.) that apply to the **outer** pytest run that collects and executes the test
  suite.
- `pytest_plugins = ["pytester"]` is a **plugin-activation** mechanism, unrelated to ini options,
  that simply makes the `pytester`/`testdir` fixtures available for use.
- The one place they *can* interact is `-p pytester` via `addopts` in
  `[tool.pytest.ini_options]` — that's simply option 2 above expressed through config instead of
  the CLI. Either mechanism (top-level `conftest.py` declaration, or `-p pytester` whether typed
  on the CLI or baked into `addopts`) is equivalent; pytest's plugin manager treats them the same
  way.
- `pytester_example_dir` is a separate, `pytester`-specific ini option (used only by
  `pytester.copy_example()`) and can be set inside `[tool.pytest.ini_options]` like any other ini
  key.

## 2. How the plugin's own entry point gets picked up inside a `pytester` sub-run

This is the part that trips people up, and it's explicitly documented in a real pytest
maintainer answer
([pytest-dev/pytest discussion #11703](https://github.com/pytest-dev/pytest/discussions/11703)):

> "Pytester is unable to discover local plugins when testing in a tmpdir. If the conftest is not
> part of the collection tree it's simply never scanned by the nested pytest."
>
> The recommended approach for testing a *packaged* plugin is to have an **editable install** and
> rely on the entry point.

Concretely, for a `uv` project:

- Run **`uv sync`** (or `uv pip install -e .`) so the package — including its
  `[project.entry-points.pytest11]` entry — is installed in the project's virtual environment in
  **editable mode**. This is what makes `importlib.metadata` (and therefore pytest's own
  `-p`/entry-point plugin discovery) see `pytest_ruff_markdown` as an installed plugin at all,
  the same way it would for any consumer's environment.
- Once that editable install exists, a **`runpytest_subprocess()`** call from within a `pytester`
  test spawns a brand-new pytest process that boots from scratch and does its own plugin
  discovery via `importlib.metadata` entry points — so it picks up the installed
  `pytest_ruff_markdown` plugin automatically, with **no extra wiring needed** in the test.
  `runpytest_subprocess` is the closer-to-reality simulation precisely because it goes through
  real process bootstrap/entry-point discovery, unlike `runpytest_inprocess`.
- **`runpytest()`** (no suffix) dispatches to either `_inprocess` or `_subprocess` depending on
  the `--runpytest` CLI flag (default: `inprocess`). For entry-point-based plugin discovery to
  be exercised, tests must either force `runpytest_subprocess()` explicitly, or the suite must be
  invoked with `--runpytest=subprocess`.
- **`pytester.plugins = [...]`** is a *different, complementary* mechanism: it directly injects a
  plugin object/module *by reference* (or by already-registered name) into the `pytester`-managed
  run, without going through entry-point discovery at all. It's the right tool when you want to
  test a *loose* plugin module (not yet packaged/installed) or want fast in-process tests. It does
  **not** by itself pick up `[project.entry-points.pytest11]`.
- **`pytester.syspathinsert()`** only affects Python import resolution (`sys.path`) for modules —
  it does not register anything as a pytest plugin/entry point on its own. It's useful if a test
  needs to `import` a helper module from the source tree inside the spawned run, not for making
  the plugin's hooks discoverable.

**Bottom line:** for testing that our real `pytest11` entry point is wired correctly end-to-end
(the thing this project actually cares about), the sub-run must go through **editable install +
`runpytest_subprocess()`**. `uv sync` must have been run (as it already is, as part of normal dev
setup / CI `uv sync` step) before `uv run pytest` executes the outer suite.

## 3. Concrete test-writing pattern

Pattern combining `pytester.makefile(...)` and `runpytest`, based on the official API reference
([pytest reference: Pytester](https://docs.pytest.org/en/stable/reference/reference.html#pytester))
and the real-world usage seen in `pytest-cov`'s and `pytest-mock`'s test suites
([pytest-cov `tests/test_pytest_cov.py`](https://github.com/pytest-dev/pytest-cov/blob/master/tests/test_pytest_cov.py),
[pytest-mock `tests/test_pytest_mock.py`](https://github.com/pytest-dev/pytest-mock/blob/main/tests/test_pytest_mock.py)):

```python
# conftest.py (repo root)
pytest_plugins = ["pytester"]
```

```toml
# pyproject.toml
[project.entry-points.pytest11]
ruff_markdown = "pytest_ruff_markdown"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```python
# tests/test_plugin_integration.py
def test_markdown_examples_are_collected(pytester):
    # Write a synthetic markdown fixture into the isolated tmp dir
    pytester.makefile(
        ".md",
        example="""
        ```python
        assert 1 + 1 == 2
        ```
        """,
    )

    # Optional: a minimal pyproject.toml / ini for the sub-run, if the plugin
    # needs its own config to activate collection
    pytester.makepyprojecttoml(
        """
        [tool.pytest.ini_options]
        addopts = "--markdown"
        """
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*1 passed*"])
```

Key points from the API reference:

- `pytester.makefile(ext, *args, **kwargs)` — generic file writer; `.md` is a perfectly valid
  `ext` for writing our synthetic markdown fixtures (there's no `makemarkdownfile` helper, so
  `makefile(".md", ...)` is the correct primitive — same category as `maketxtfile`/`makepyfile`,
  which are themselves thin wrappers around `makefile`).
- `pytester.makepyprojecttoml(source)` (pytest ≥ 6.0) — writes a `pyproject.toml` into the
  isolated dir when the sub-run needs its own `[tool.pytest.ini_options]`.
- `pytester.runpytest_subprocess()` — runs the isolated dir's tests as a real subprocess, going
  through normal entry-point plugin discovery (see §2). Prefer this over the bare
  `runpytest()`/`runpytest_inprocess()` whenever the test's purpose is to prove the packaged
  plugin registers and activates correctly.
- `result.assert_outcomes(passed=1, failed=0, skipped=0, …)` — asserts exact pass/fail/skip
  counts.
- `result.stdout.fnmatch_lines([...])` — fnmatch-style (glob) assertions against captured stdout,
  handy for checking specific diagnostic/report lines without being byte-exact.

## 4. How comparable real plugins structure their `pytester` suites

- **`pytest-cov`** (`tests/test_pytest_cov.py`,
  [source](https://github.com/pytest-dev/pytest-cov/blob/master/tests/test_pytest_cov.py)):
  uses the fixture (aliased `testdir`/`pytester`), builds synthetic test scripts with
  `makepyfile(...)`, writes an auxiliary `.coveragerc` file directly via
  `testdir.tmpdir.join('.coveragerc').write(...)`, then calls `testdir.runpytest(...)` with the
  plugin's real CLI flags (`--cov=...`, `--cov-report=...`) and asserts via
  `result.stdout.fnmatch_lines([...])` plus `assert result.ret == 0`. This is a working example
  of a packaged, entry-point-registered plugin being exercised end-to-end through `pytester`.
- **`pytest-mock`** (`tests/test_pytest_mock.py`,
  [source](https://github.com/pytest-dev/pytest-mock/blob/main/tests/test_pytest_mock.py)):
  declares `pytest_plugins = "pytester"` once near the top of the test module, then has many
  small tests that call `testdir.makepyfile(...)` (+ sometimes `testdir.makeini(...)`) followed
  by `testdir.runpytest_subprocess(...)`, asserting either `result.ret` directly,
  `result.assert_outcomes(passed=..., failed=...)`, or `result.stdout.fnmatch_lines([...])`. Its
  `pyproject.toml` declares the plugin the same way we plan to:
  `[project.entry-points.pytest11]` → `pytest_mock = "pytest_mock"`, with no special
  `[tool.pytest.ini_options]` needed for the mechanism to work — confirming the entry-point +
  editable-install path is sufficient and is the standard approach, not something project-specific.
- **`pytest-examples`** (pydantic project): its own suite
  (`tests/test_find_examples.py`, `tests/test_lint.py`, etc.) tests its Markdown/docstring-example
  extraction logic directly with fixture files under `tests/`, rather than via `pytester`
  sub-runs — i.e. it unit-tests its extraction machinery in-process and does not need a nested
  pytest invocation to prove itself, since it isn't primarily a pytest11-registered collection
  hook. This is a useful counter-example: `pytester` sub-runs are worth reserving specifically
  for verifying the parts of `pytest-ruff-markdown` that hook into pytest's own collection
  (i.e. confirming the `pytest11` entry point + collection hooks work when pytest boots for
  real), while pure extraction/parsing logic can be tested as plain unit tests without `pytester`
  at all.
- A dedicated `pytest-markdown-docs` project was not found as a currently maintained/public
  GitHub repository at the time of this research; no source could be inspected for it.

## Sources

- pytest docs — [Testing plugins](https://docs.pytest.org/en/stable/how-to/writing_plugins.html#testing-plugins)
- pytest docs — [API reference: Pytester](https://docs.pytest.org/en/stable/reference/reference.html#pytester)
- pytest docs — [Deprecations: `pytest_plugins` in non-top-level conftest.py](https://docs.pytest.org/en/stable/deprecations.html)
- pytest-dev/pytest — [Discussion #11703, "Testing plugins" example doesn't work](https://github.com/pytest-dev/pytest/discussions/11703)
- pytest-cov — [`tests/test_pytest_cov.py`](https://github.com/pytest-dev/pytest-cov/blob/master/tests/test_pytest_cov.py)
- pytest-mock — [`tests/test_pytest_mock.py`](https://github.com/pytest-dev/pytest-mock/blob/main/tests/test_pytest_mock.py), [`pyproject.toml`](https://github.com/pytest-dev/pytest-mock/blob/main/pyproject.toml)
- pydantic/pytest-examples — [`tests/` directory listing](https://github.com/pydantic/pytest-examples/tree/main/tests)
