# Inspector Design

## Sources

- D-Wave Inspector docs: https://docs.dwavequantum.com/en/latest/ocean/api_ref_inspector/
- `dwave.inspector.show`: https://docs.dwavequantum.com/en/latest/ocean/api_ref_inspector/generated/dwave.inspector.show.html
- D-Wave Inspector repo: https://github.com/dwavesystems/dwave-inspector
- Embedding examples: https://docs.dwavequantum.com/en/latest/quantum_research/embedding_guidance.html

## API

```python
report = Inspector.from_result(result)
report.show()

Inspector.compare([thrml_result, neal_result]).show()
```

## v0 Sections

Summary:

- best energy;
- best feasible energy;
- feasibility rate;
- runtime;
- flags.

Traces:

- energy;
- best-so-far;
- chain quantiles.

Diagnostics:

- autocorrelation;
- ESS-style estimate;
- chain disagreement;
- warning flags.

Diversity:

- unique states;
- top state frequencies;
- Hamming histogram;
- energy versus distance-to-best.

Topology:

- problem graph;
- block coloring;
- block sizes;
- block flip rates.

Constraints:

- broken-constraint distribution;
- best feasible/infeasible samples;
- penalty contribution if available.

Comparison:

- best energy by solver;
- time-to-target;
- energy distribution;
- metadata table.

## Artifacts

- `report.html` or `report.md`
- `summary.json`
- `samples.npz` or `samples.parquet`
- `traces.npz`
- `problem.json`
- `run_metadata.json`

## Flags

- `poor_mixing`
- `low_ess`
- `chain_disagreement`
- `high_sample_concentration` (observation, not a failure flag)
- `no_recent_improvement`
- `low_feasibility`
- `bad_schedule`
- `block_stuck`
- `conversion_unverified`
