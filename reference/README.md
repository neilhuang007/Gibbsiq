# Reference Index

Research snapshot: 2026-05-17.

## Start Here

- [Why this project matters](why-this-project-matters.md)
- [Impact audit](impact-audit-2026-05-28.md)
- [Downloaded paper pack](downloaded-papers.md)
- [Source map](source-map.md)
- [Research gaps](research-gaps.md)
- [Roadmap](00-roadmap/README.md)

## Technical Notes

- [THRML runtime](01-architecture/thrml-runtime.md)
- [QUBO/BQM API](02-interfaces/qubo-bqm-api.md)
- [THRML Gibbs sampler](03-samplers/thrml-gibbs-implementation.md)
- [Baseline solvers](03-samplers/baseline-solvers.md)
- [Diagnostics](04-diagnostics/mixing-quality.md)
- [Theory](05-theory/probabilistic-computing-and-pbits.md)
- [Benchmark plan](06-benchmarks/benchmark-plan.md)
- [Inspector design](07-inspector/inspector-design.md)
- [Evaluation framework](08-evaluation/README.md)

## Rules for Future Agents

- Prefer primary sources: official docs, papers, source repos.
- Use [the equation audit](08-evaluation/equation-audit.md) for math; raw PDF transcripts are not authoritative.
- Run or preserve [evaluation fixtures](08-evaluation/fixtures/README.md) before changing conventions.
- Keep docs short and implementation-oriented.
- Record assumptions and sign conventions.
- Do not assume THRML provides QUBO/BQM conversion, diagnostics, inspector, or baselines.
