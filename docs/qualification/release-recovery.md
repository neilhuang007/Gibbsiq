# Release recovery

Use this procedure when a released version produces an incorrect result or
cannot be installed.

1. Reproduce the problem in a fresh environment using the exact affected version.
2. Record the failing command, environment, and minimal input.
3. Add a behavioral regression test and fix the cause.
4. Run the contributor checks and installed-wheel verification.
5. Release the correction under a new version and describe the fix in the
   changelog.
6. If the affected version should leave automatic dependency resolution, yank
   it through the package index and provide a reason.

Retain the affected artifact and reproduction evidence for diagnosis. Versioned
releases give users an explicit upgrade path and preserve reproducibility.

Follow the [release checklist](local-release-contract.md) for the corrected
version.
