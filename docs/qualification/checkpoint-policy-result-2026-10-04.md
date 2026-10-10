# Frozen checkpoint policy result: 4 October 2026

Neither policy qualified under the frozen contract. The heterogeneous allocation
had worse observed loss than the equal-work uniform baseline; all three
conservative statistical decisions remained **inconclusive**. No policy was
exported.

## Experiment

Source: `52cdd376cf9b1159d46275c841f404fb76f93000`. The pinned Z1T-0 checkpoint
was loaded with its full 50,257-output vocabulary head. Its numerical parameter
identity was `02577f67eade622036b35eb2200e890045bea1b626ddac1a2004afc882246dcc`;
upstream source was sparse-transformers commit
`13051e90df9669be5b8f9f34fb097329fa82f674`.

Four newly authored texts contributed four teacher-forced targets each, with
32 independently randomized whole-corpus replicates per policy. The texts and
token sequences differ from the earlier study; their membership in model
training data is unknown. The result concerns execution randomness on these
fixed inputs only. The 512 target evaluations per policy are not 512 independent
replicates.

The software profile sampled `blocks.3.attn.out_proj` and `blocks.3.mlp.proj2`.
The frozen heterogeneous policy used 8/128 draws; the uniform baseline used
68/68. Both operations have 12,288 outputs, so both policies use 6,684,672
modeled spin draws per four-token forward and 26,738,688 per corpus. Policy
order alternated by replicate; policy/document streams were separate.

## Quality

The reference NLL was 8.231684807 nats/target. Loss was capped at 16 for the
qualification contract; uncapped NLL is descriptive. Total alpha 0.05 was split
equally among the three fixed-sample Hoeffding intervals.

| Policy | Mean raw NLL | Mean capped NLL | Cap hits / target evaluations |
| --- | ---: | ---: | ---: |
| Heterogeneous 8/128 | 12.314868409 | 11.668249030 | 137 / 512 |
| Uniform 68/68 | 9.516488961 | 9.502749937 | 9 / 512 |

| Comparison, capped NLL difference | Estimate | Confidence interval | Upper margin | Decision |
| --- | ---: | --- | ---: | --- |
| Heterogeneous minus numerical | 3.436564223 | [-0.939503300, 7.768315193] | 0.50 | Inconclusive |
| Uniform minus numerical | 1.271065130 | [-3.105002393, 5.647132654] | 0.50 | Inconclusive |
| Heterogeneous minus uniform | 2.165499093 | [-6.586635954, 10.917634140] | 0.25 | Inconclusive |

Before inference, the protocol calculated 2,452 runs for a 0.5-nat
numerical-comparison half-width and 39,220 runs for a 0.25-nat paired half-width.
The bounded 32-run study does not establish a narrow guarantee. The margins and
procedure were not changed after observing results.

## Cost and verification

Median full-corpus forward, host-transfer, and loss time was 1.092669 seconds for
the heterogeneous policy and 1.095023 seconds for the uniform policy. The
corresponding forward-plus-transfer medians were 0.935245 and 0.933926 seconds.
These are serial CPU software measurements with the complete model head; equal
modeled work does not imply equal latency. This is not a speedup result.

Checkpoint loading took 7.609274 seconds, the first one-token smoke took 2.896801
seconds, and the experiment took 82.942641 seconds. The enclosing service ran
for 95.085 seconds, consumed 218.227 CPU seconds, and the process recorded peak
RSS 9.475 GiB. Limits were four cores, 16 GiB, no swap, and 1,900 seconds.

Five rotated warmed measurements on the first document gave a 0.194748-second
direct forward/transfer/loss median. The paired observed-versus-wrapper
forward/transfer overhead median was -15.68%. This noisy, small timing sample
does not establish that observation makes execution faster. Energy and
physical-device performance were not measured.

Direct and observed logits matched exactly on all four documents. An independent
SciPy log-sum-exp calculation agreed with the loss evaluator. Both policy replay
checks passed. Independent checks confirmed all 64 unique parent streams,
replicate counts, execution order, target accounting, work equivalence, and the
three interval calculations.

## Reproduction

The recorded environment was Linux x86_64, Python 3.12.10, JAX/JAXlib 0.10.2,
Equinox 0.13.8, NumPy 2.4.6, SciPy 1.18.1, tiktoken 0.14.0, and pinned Z1T 0.0.1.
The experiment ran from the source checkout through explicit `PYTHONPATH` and
the pinned dependency environment, rather than an installed wheel.

Follow the [checkpoint setup](trained-checkpoint-verification.md), select the
source commit above, and run with the same CPU environment and a new output
directory:

```console
python -m tools.qualification.verify_trained_checkpoint /path/to/weights/model.eqx /path/to/new-run --policy-study
```

The command saves `protocol.json` before inference, followed by
`load-and-smoke.json` and `policy-results.json` with per-replicate losses, timings,
and stream identities. It refuses to overwrite an existing attempt. Checkpoint
weights are not redistributed.
