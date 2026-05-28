# Roadmap

## Stages

0. [Research and framing](stage-00-research-and-framing.md)
1. [Core model compatibility](stage-01-core-model-compatibility.md)
2. [First THRML sampler](stage-02-first-thrml-sampler.md)
3. [Diagnostics pipeline](stage-03-diagnostics-pipeline.md)
4. [Inspector and reporting](stage-04-inspector-and-reporting.md)
5. [Baselines and benchmarks](stage-05-baselines-and-benchmarks.md)
6. [Adaptive hardware-aware runtime](stage-06-adaptive-hardware-runtime.md)

## Dependencies

```text
0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6
```

Parallelizable:

- diagnostics can start from fixtures after Stage 1;
- benchmark loaders can start after Stage 1;
- inspector can start from mock `SampleResult` artifacts.
