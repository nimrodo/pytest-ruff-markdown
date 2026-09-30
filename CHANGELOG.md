# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and this project follows
[semantic versioning](https://semver.org/).

## [0.2.0] - 2026-09-30

### Added

- `pytest-ruff-markdown-format` formats a `continues` chain as one unit, so a
  block that is only valid in context (for example an indented method body
  after a class block) formats cleanly instead of failing. A failing chain is
  reported once, at the block ruff blamed, and left untouched. (#37)

### Fixed

- Linting runs the `ruff` installed alongside the plugin instead of whatever
  is first on `PATH`, which failed without an activated virtualenv. It also
  passes `--no-fix`, so a project's `fix = true` can no longer corrupt the
  output; no longer reports `W292` on every block; reads and writes UTF-8
  regardless of locale; and reports trailing blank lines in a block (`W391`).
  (#34)
- Fence parsing follows CommonMark: a closing fence may be longer than the
  opener or indented up to three spaces, fences with any info string are
  tracked so a `python` fence nested inside another fence is literal text,
  and a `python` fence longer than three backticks is a block. Previously a
  longer or indented closer merged the following prose and blocks into one.
  (#35)
- The formatter CLI:
  - keeps each file's own line endings, so CRLF is no longer turned into LF;
  - treats only `\n` and `\r\n` as line endings, so prose containing form feed
    or similar is no longer rewritten and block line numbers match editors;
  - reports a block `ruff` cannot format as `path:line: ...` and exits `2`,
    instead of aborting with a traceback;
  - reports a nonexistent path as a usage error (exit `2`);
  - skips hidden directories, `node_modules` and virtualenvs when walking a
    directory;
  - formats away trailing blank lines inside a block, as `ruff` does for a
    file. (#36)

## [0.1.0] - 2026-09-27

- Initial release: lint fenced `python` blocks in Markdown files with `ruff`,
  with skip and continues markers, plus the `pytest-ruff-markdown-format`
  CLI.
