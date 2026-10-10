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

Configure a [PyPI Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
on the existing `gibbsiq` project with owner `neilhuang007`, repository
`Gibbsiq`, workflow filename `publish.yml`, and environment `pypi`.
The matching GitHub environment belongs in the repository's Settings →
Environments. Restrict deployments to `master`; add a required reviewer if the
release process needs manual approval. No PyPI password or long-lived token is
needed by the workflow.

Run **Publish to PyPI** from GitHub Actions on `master`, supplying the successful
master **CI run ID** and exact version. Leave `publish` unchecked for a rehearsal.
The workflow rejects failed, pull-request, foreign-repository, and non-master
runs. It retrieves the `release-distributions` artifact, verifies the wheel and
sdist metadata, and retains the source commit and SHA-256 hashes. It never
rebuilds the distributions. CI artifacts expire after seven days; if needed,
rerun CI for the reviewed commit before selecting its new artifacts.

Once the rehearsal passes and the publisher is configured, run the same inputs
with `publish` checked. The separate publishing job uses short-lived GitHub
identity credentials. A final job checks both published artifact hashes,
installs the exact version from PyPI with hash verification in a fresh external
environment, and runs the installed-package smoke test.

Tag the tested source commit and publish release notes from the changelog.
After successful index verification, start the next unreleased changelog entry.

Keep the tested distributions and CI logs with the release. See
[release recovery](release-recovery.md) for handling a defective version.
