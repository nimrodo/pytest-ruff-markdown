# Execution: how should the plugin invoke ruff?

Research for [nimrodo/pytest-ruff-markdown#3](https://github.com/nimrodo/pytest-ruff-markdown/issues/3), child of the wayfinder map [#2](https://github.com/nimrodo/pytest-ruff-markdown/issues/2).

Date: 2026-09-25. Ruff version used for empirical tests: `0.16.9` (`uv tool run ruff --version`).

## Summary of recommendations

| Question | Answer |
| --- | --- |
| Stdin vs temp file | **Stdin** (`ruff check -` + `--stdin-filename`), with the synthetic filename built as a **real, absolute path** derived from the markdown file's actual location on disk (e.g. `<markdown_dir>/<md_stem>__block<N>.py`). No cwd change or `--config` needed. |
| Config discovery via `--stdin-filename` | **Yes, it works** — but only if the filename you pass resolves (after joining with cwd, if relative) to a path whose *ancestor directories* actually contain the target `ruff.toml`/`pyproject.toml`. Confirmed empirically and by a Ruff maintainer. |
| `--output-format=json` | Correct, stable, structured-output flag. Confirmed present via `--help` and produces well-formed JSON. Note a schema change in 0.16.0 (nullable `filename`/`location` fields) to defend against. |
| Minimum `ruff` version | Recommend pinning `ruff>=0.4.0` as a practical floor (see reasoning below); the *absolute* correctness floor for `--output-format` alone is `0.1.0`. |
| Subprocess batching | One process per code block is *acceptable but wasteful*; prefer batching multiple blocks from the same markdown file (or run) into fewer `ruff check` invocations using real temp files, since `ruff check` natively accepts multiple `[FILES]...` args and stdin mode only accepts one stream per call. |

---

## 1. Stdin vs temp file

### What the CLI supports

`ruff check --help` (v0.16.9):

```
Usage: ruff check [OPTIONS] [FILES]...

Arguments:
  [FILES]...
          List of files or directories to check, or `-` to read from stdin [default: .]
      --stdin-filename <STDIN_FILENAME>
          The name of the file when passing it through stdin
```

So stdin mode is `ruff check - --stdin-filename <path>`, and `--stdin-filename` exists specifically to give the piped content a virtual identity.

### What `--stdin-filename` is actually for

From a Ruff maintainer (`sharkdp`) on [astral-sh/ruff#17307 "Does `--stdin-filename` actually do anything?"](https://github.com/astral-sh/ruff/issues/17307):

> "It is used internally as a placeholder for the 'file' that Ruff reads from STDIN... Setting it to the filename that you're piping in from your editor can be useful because it will generate correct references (and potentially clickable links, depending on your terminal) in those diagnostic messages."

and from `MichaReiser` (Ruff maintainer) in the same thread:

> "The filename is also used to infer the file type. E.g. a file ending in `.ipynb` is treated as a notebook and a file ending in `.pyi` is a stub file. Different rules apply to those files."

So `--stdin-filename` drives (a) diagnostic path display, (b) file-type inference by extension, and — critically for this question — (c) configuration discovery (next section).

### Recommendation

Use stdin, not a real temp file:

- No filesystem writes/cleanup, no race conditions with parallel test workers, nothing to `.gitignore`.
- `--stdin-filename` gives ruff everything a real file would (config discovery, correct diagnostic paths, extension-based rule selection) as long as the synthetic path is constructed correctly (see below).
- Temp files would only be preferable if we needed ruff to *write back* to disk (`--fix` applying edits in place) — not our use case; we only need diagnostics.

A synthetic filename like `<the_markdown_file's_real_directory>/<markdown_stem>__block<N>.py` (e.g. `docs/guide.md` → `docs/guide__block1.py`) preserves both the correct config-discovery ancestry *and* produces a readable, non-colliding diagnostic path per block.

---

## 2. Does `--stdin-filename` give ruff enough context for config discovery?

**Yes — empirically confirmed and confirmed by a maintainer — provided the path you pass is (or resolves to) a real path under the markdown file's actual directory tree.** No explicit cwd change or `--config` is required.

### Maintainer confirmation

[astral-sh/ruff#17405](https://github.com/astral-sh/ruff/issues/17405) is a report that stdin config discovery "doesn't use pyproject.toml" — the repro was `cd repro/src && ruff check --stdin-filename stdin - < repro.py`, where `pyproject.toml` lives in `repro/`, not `repro/src/`. Maintainer `dylwil3` explained:

> "When searching for a configuration, we look at ancestors of the current working directory for configuration files - but if you pass in a stdin filename, we use ancestors of whatever path you give."

I.e. **if `--stdin-filename` is relative, it's resolved against cwd, and ancestor search then starts from *that* resolved path — not from cwd itself.** Since the repro's `--stdin-filename stdin` had no directory component, it resolved to `repro/src/stdin`, whose ancestor `repro/src/` has no config, and `ruff` didn't walk far enough to find `repro/pyproject.toml` because the *cwd itself* (`repro/src`) was being used as the search root by default — passing any relative filename anchors the search at that filename's resolved location, so a bare `stdin` filename anchors it exactly where cwd already was. The reporter confirmed the fix was to make the path reflect the *real* relative or absolute location, e.g. `--stdin-filename ../stdin` from `repro/src`, or run from `repro/` with `--stdin-filename stdin` over `src/repro.py`'s content.

Maintainer `MichaReiser` added:

> "Making the stdin path absolute does sound reasonable to me (unless it is already absolute)."

This confirms the mechanism: **ruff walks up from `--stdin-filename`'s resolved directory**, not from cwd, and the fix/best-practice is to pass an **absolute** path so there's no cwd-dependent ambiguity at all. This behavior originates in [PR #1281, "Use `--stdin-filename` when resolving configuration files"](https://github.com/astral-sh/ruff/pull/1281) (merged 2022-12-18), whose description states the pre-fix bug directly:

> "Currently, when `ruff` is called with `--stdin-filename`, it does not use this value when searching for a configuration file... `black` finds the expected project-local `pyproject.toml`... This PR makes `ruff` find configuration files more like `black` does when `--stdin-filename` is passed."

### Empirical verification (this session)

Ran against `ruff 0.16.9` in three scenarios, with a `pyproject.toml` at `$WORK` setting `line-length = 20` and `select = ["E501"]`, and a 59-character Python line piped via stdin:

```console
# cwd = $WORK (repo root), stdin-filename relative but rooted correctly
$ echo "$CODE" | ruff check - --stdin-filename sub/docs/example.md_block1.py --output-format concise
sub/docs/example.md_block1.py:1:21: E501 Line too long (59 > 20)
Found 1 error.

# cwd = /tmp (UNRELATED to $WORK), stdin-filename is an ABSOLUTE path into $WORK
$ echo "$CODE" | ruff check - --stdin-filename "$WORK/sub/docs/example.md_block1.py" --output-format concise
/tmp/ruff-stdin-test/sub/docs/example.md_block1.py:1:21: E501 Line too long (59 > 20)
Found 1 error.

# cwd = /tmp, stdin-filename is a bare synthetic name with no real directory context
$ echo "$CODE" | ruff check - --stdin-filename example.md_block1.py --output-format concise
All checks passed!   # <- config NOT found; default line-length (88) used, so no violation
```

A second test confirmed discovery follows the *closest ancestor config to the stdin-filename path*, not to cwd: with cwd at a repo root that has **no** config, and a `ruff.toml` (`line-length = 20`) placed only in `nested/`, passing `--stdin-filename "$WORK/nested/docs/readme.md_block1.py"` still picked up `nested/ruff.toml` and flagged the line — matching Ruff's documented ["closest config file in the directory hierarchy" resolution](https://docs.astral.sh/ruff/configuration/) rule, extended to the stdin-filename's directory instead of cwd's.

### Practical implication for this plugin

- Build the synthetic path as an **absolute path** (`(markdown_file.resolve().parent / f"{markdown_file.stem}__block{n}.py")` or similar) so behavior is independent of whatever cwd `pytest` happens to run from (pytest often runs from the repo root, but plugins shouldn't assume that).
- No need for `--config` or an explicit `cwd=` in the subprocess call — passing an absolute, correctly-located `--stdin-filename` is sufficient and is exactly what Ruff's own maintainers recommend as the robust fix (see `MichaReiser` quote above).
- If we ever *do* want to force a specific config file regardless of location (e.g. a project-wide override), `--config <path>` remains available per `ruff check --help`, but it's not required for the default "respect the project's own config" behavior this plugin wants.

---

## 3. `--output-format=json`

Confirmed via `ruff check --help` (v0.16.9):

```
--output-format <OUTPUT_FORMAT>
    Output serialization format for violations. The default serialization format is "full"
    [env: RUFF_OUTPUT_FORMAT=]
    [possible values: concise, full, json, json-lines, junit, grouped, github, gitlab, pylint, rdjson, azure, sarif]
```

and the [Ruff settings docs](https://docs.astral.sh/ruff/settings/#output-format) list `json` explicitly as one of the supported, named output formats (alongside `json-lines`, `junit`, `sarif`, etc. — all clearly machine-readable/structured formats, as opposed to `full`/`concise`/`grouped` which are human-readable text).

Empirically, `ruff check - --stdin-filename x.py --output-format json` on this session produced well-formed JSON with `filename`, `code`, `message`, `location`/`end_location` (row/column), `fix`, `severity`, `url`, and `noqa_row` fields — a stable, parseable shape.

**Caveat to design around:** the [v0.16.0 changelog/blog](https://astral.sh/blog/ruff-v0.16.0) notes:

> "The `filename`, `location`, `end_location`, `fix.edits[].location`, and `fix.edits[].end_location` fields in the JSON output format may now be null rather than defaulting to the empty string and row 1, column 1, respectively."

This is a real, documented shape change for consumers of `--output-format=json` on ruff `>=0.16.0`. **The plugin's JSON parser must treat `location`/`end_location`/`filename` as optional/nullable**, not assume they're always populated, if it supports ruff versions spanning this change.

`--output-format=json` is the right, stable, structured-output choice — confirmed correct, no need to parse human-readable `full`/`concise` text.

---

## 4. Minimum `ruff` version to pin

Ruff has **no stable CLI/API guarantee** — per the [versioning policy docs](https://docs.astral.sh/ruff/versioning/):

> "Ruff does not yet have a stable API; once Ruff's API is stable, the major version number and semantic versioning will be used." Breaking changes bump the **minor** version; bug fixes bump **patch**.

So any floor is a practical judgment call, not a guarantee from Ruff itself. Relevant dated facts:

- **`--stdin-filename`-driven config discovery** (the behavior this plugin depends on) was introduced in [PR #1281](https://github.com/astral-sh/ruff/pull/1281), merged **2022-12-18** — very early, pre-`0.1` versions of Ruff (Ruff was on `0.0.x` releases at the time; e.g. `0.0.246` was released in Feb 2023). This has been stable/correct (per the maintainer confirmation in #17405, April 2025, describing it as intended, not buggy) ever since.
- **`--output-format` as the sole, non-deprecated flag name** (superseding the old `--format`) landed with **Ruff `v0.1.0`, released 2023-10-16**. The `v0.1.0` release notes state: *"The deprecated `format` setting has been removed... The `--format` option has been removed from `ruff check`, use `--output-format` instead."* Before `0.1.0`, `--format=json` also worked (json output itself is much older), but `--output-format` specifically requires `>=0.1.0`.
- **JSON output schema changed** (nullable `filename`/`location` fields) in **Ruff `0.16.0`** (2025) — not a floor-raising issue, but code parsing the JSON needs to tolerate both old and new shapes if it supports a version range spanning `0.16.0`.

### Recommendation

Pin **`ruff>=0.4.0`** in `pyproject.toml`.

Reasoning: the *strict correctness floor* for everything this plugin needs (`--stdin-filename` config discovery + non-deprecated `--output-format`) is `0.1.0` (Oct 2023). But `0.1.0` was the version immediately after a breaking flag rename and is over two years old at the time of writing with a fast-moving, explicitly-unstable-CLI tool — pinning right at the correctness floor leaves no margin for edge-case bugs fixed in the following months. `0.4.0` (released ~April 2024) gives roughly six months of stabilization past the `--output-format` rename while still being a low, permissive floor that doesn't exclude reasonably-recent-but-not-bleeding-edge user environments. This is an engineering judgment call, not a hard requirement from Ruff's docs — teams that want to move the floor up to something even more current (e.g. `>=0.6.0`) to reduce support surface would also be reasonable.

Either way, the JSON-parsing code should be written defensively (treat `filename`/`location`/`end_location` as optional) so it doesn't hard-fail against the `0.16.0` schema change regardless of the declared floor.

---

## 5. One subprocess per code block, or batch?

Ruff's docs/CLI don't directly answer "should a *linting tool built on ruff* batch calls" — this is a design question for this plugin, but the CLI's own capabilities point the answer:

- `ruff check --help` shows the positional arg is `[FILES]...` — **plural**, "List of files or directories to check, **or `-` to read from stdin**". Ruff natively supports checking many real files in one invocation, and internally parallelizes: Ruff is designed to lint whole projects in a single process launch, which is a large part of its "extremely fast" positioning.
- Stdin mode, by contrast, accepts exactly **one** anonymous input stream per invocation (`ruff check -`) — there's no documented mechanism to pipe multiple distinct "files" through a single stdin call with different `--stdin-filename`s each. So **stdin mode is inherently one-block-per-process.**

### Recommendation

- **One subprocess per code block via stdin is functionally correct and fine for small/medium markdown suites** — process startup cost is the main overhead (ruff's own linting work is fast), and correctness/isolation (each block gets its own synthetic filename, own config resolution) is simplest to reason about this way.
- **For markdown-heavy repos where per-process overhead matters**, prefer **batching within a single markdown file** (or across a whole pytest session) by writing extracted blocks to real temporary files (one temp dir, one file per block, correctly nested to preserve config discovery, mirroring the real markdown file's directory) and invoking `ruff check <path1> <path2> ... --output-format=json` **once** — using the plural `[FILES]...` capability instead of N stdin calls. This trades "no temp files" for "far fewer process spawns," and is a legitimate escape hatch if profiling shows subprocess-per-block is the bottleneck. It should not be the default (it reintroduces filesystem writes/cleanup complexity for what is, in the common case, a small number of code blocks), but the plugin should be structured so batching can be added later without an API-breaking change (e.g. an internal `run_ruff(blocks: list[Block]) -> list[Diagnostics]` seam that starts by looping over stdin calls one at a time).

No official Ruff guidance says one way is "wrong" — this is purely a startup-cost-vs-complexity tradeoff for the plugin's own implementation.

---

## Sources

- `ruff check --help` (Ruff 0.16.9, run locally via `uv tool run ruff check --help`)
- [Ruff Configuration docs](https://docs.astral.sh/ruff/configuration/) — config file discovery ("closest config file in the directory hierarchy")
- [Ruff Settings docs — `output-format`](https://docs.astral.sh/ruff/settings/#output-format)
- [Ruff Versioning policy](https://docs.astral.sh/ruff/versioning/)
- [astral-sh/ruff#17307 — "Does `--stdin-filename` actually do anything?"](https://github.com/astral-sh/ruff/issues/17307) (maintainers `sharkdp`, `MichaReiser`)
- [astral-sh/ruff#17405 — "ruff check with file read from stdin does not use options from pyproject.toml when `--stdin-filename` argument is used"](https://github.com/astral-sh/ruff/issues/17405) (maintainer `dylwil3`, `MichaReiser`)
- [astral-sh/ruff#1281 — "Use `--stdin-filename` when resolving configuration files"](https://github.com/astral-sh/ruff/pull/1281) (merged 2022-12-18)
- [Ruff `v0.1.0` release notes](https://github.com/astral-sh/ruff/releases/tag/v0.1.0) — removal of deprecated `--format`
- [Ruff `v0.16.0` blog post](https://astral.sh/blog/ruff-v0.16.0) — nullable JSON fields
- Empirical tests run in this session against `ruff 0.16.9` (see transcripts above; reproducible via `uv tool run ruff check ...`)
