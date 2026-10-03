# Release process

Gibbsiq releases use a reviewed commit, a curated changelog, and verified source
and wheel distributions. This follows the workflow described by
[Pallets](https://palletsprojects.com/contributing/release).

## Prepare

1. Update the version in `src/gibbsiq/__init__.py`.
2. Review user-facing changes in `CHANGELOG.md`.
3. Run the checks in [CONTRIBUTING.md](../../CONTRIBUTING.md).
4. Confirm the CI core, numerical integration, and distribution jobs pass.

## Build and verify

Build into a fresh output directory:

```console
python -m build --outdir dist/release
python -m twine check --strict dist/release/*
```

The default build creates an sdist, then builds the wheel from that sdist.
Install that wheel into a fresh environment with `--no-deps`.

From a directory outside the checkout, run the installed-package check using
the fresh environment's Python:

```console
python -I /path/to/Gibbsiq/tools/check_installed_package.py
python -m pip check
```

The check exercises packaged resources, CLI commands, qualification, regression
comparison, and policy search. CI performs this check on Linux and Windows.

## Publish

Review the exact distribution files, tag the tested commit, and upload those
files to the package index. Publish release notes from the changelog. Verify an
installation from the index, then start the next unreleased changelog entry.

Keep the tested distributions and CI logs with the release. See
[release recovery](release-recovery.md) for handling a defective version.
