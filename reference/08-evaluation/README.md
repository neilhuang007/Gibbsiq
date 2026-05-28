# Evaluation Reference

This section defines how future Gibbsiq implementations should be checked.

Use it in this order:

1. [Equation audit](equation-audit.md) - manually verified formulas that tests may rely on.
2. [Evaluation framework](evaluation-framework.md) - required test layers, pass criteria, and benchmark rules.
3. [Fixtures](fixtures/README.md) - machine-readable exact inputs and expected outputs.
4. [Implementation source candidates](source-implementation-candidates.md) - primary source repos that can be modeled or copied from when licenses permit.

Raw paper transcripts under the `papers/` folders are searchable text only. They are not math-authoritative because PDF extraction can damage equations. When a formula matters, use the equation audit and re-check the source PDF page before implementing.

