# Contributing

## Development

Set up the environment with `uv sync`, then:

```
uv run pytest                 # run the test suite
uv run ruff check .           # lint
uv run ruff format --check .  # check formatting (drop --check to apply it)
uv run ty check .             # type-check
```

`ty` is pre-1.0 and pinned to an exact version in `pyproject.toml` for that
reason — bump it deliberately, not via a loose range.

## Versioning

This project follows [semantic versioning](https://semver.org/)
(`MAJOR.MINOR.PATCH`). There is no version-bump tooling: a release is a
deliberate, manual edit to the `version` field in `pyproject.toml`, chosen
according to semver rules based on the nature of the changes since the
last release.

## Releasing

1. On `main`, with CI green, bump `version` in `pyproject.toml` per semver
   and add the release's entry to `CHANGELOG.md`, then commit both.
2. Tag that commit `vX.Y.Z` (matching the new version) and push the tag:
   `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. The `Release` workflow (`.github/workflows/release.yml`) triggers on the
   tag push, verifies the tag matches `pyproject.toml`, builds the
   package, and publishes it to PyPI via `uv publish` using PyPI's
   trusted publishing (OIDC) — no token is stored in this repo. It waits
   for manual approval in the `release` environment before publishing.

**A failed release can't be retried under the same version.** PyPI never
allows re-uploading a given version number, even after a failed or
partial publish. If a release run fails, don't re-push the same tag —
bump `PATCH` and cut a new tag instead.

**Retrying a run without re-tagging** (e.g. a transient publish failure
where the version itself was never accepted by PyPI): trigger the
`Release` workflow manually via `workflow_dispatch` with the existing
tag as input, instead of re-tagging.

## Validating against a local checkout

To manually check the plugin against a real project without adding it as a dependency, run it from your checkout with `uv run --with`:

```
uv run --with pytest-ruff-markdown@/path/to/pytest-ruff-markdown python -m pytest
```

**Invoke pytest via `python -m pytest`, not the bare `pytest` command.** Bare `pytest` can resolve to a pre-existing `pytest` executable outside the ephemeral overlay environment (for example, the target project's own `.venv/bin/pytest`) that does not have this plugin installed. When that happens it fails silently: no error, just zero `.md` files collected, or a confusing `ERROR: not found: .../README.md (no match in any of [...])` if you point it at a markdown file directly. `python -m pytest` runs pytest from the interpreter `uv run` just resolved, which guarantees it is the one with the plugin installed.

### Troubleshooting

Not collecting `.md` files? Confirm the plugin is actually registered:

```
uv run --with pytest-ruff-markdown@/path/to/pytest-ruff-markdown python -m pytest --trace-config | grep ruff_markdown
```

If nothing prints, pytest is running from an environment without the plugin installed — check which `pytest`/`python` you're invoking.
