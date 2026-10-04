# Frozen checkpoint policy result: 4 October 2026

The planned heterogeneous-policy comparison ran successfully. Neither policy
qualified under the frozen contract. The heterogeneous allocation had worse
observed loss than the equal-work uniform baseline; all three conservative
statistical decisions remained **inconclusive**. No policy was exported.

## Experiment

Source: `52cdd376cf9b1159d46275c841f404fb76f93000`. The actual pinned
Z1T-0 checkpoint was loaded with its full 50,257-output vocabulary head.
The numerical parameter identity was
`02577f67eade622036b35eb2200e890045bea1b626ddac1a2004afc882246dcc`;
upstream source was sparse-transformers commit
`13051e90df9669be5b8f9f34fb097329fa82f674`.

Four newly authored texts contributed four teacher-forced targets each, with
32 independently randomized whole-corpus replicates per policy. These texts and
token sequences differ from the earlier study. Their membership in model
training data is unknown, and the result concerns execution randomness on these
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

The intervals are wide by design. Before inference, the protocol calculated
2,452 runs for a 0.5-nat numerical-comparison half-width and 39,220 runs for a
0.25-nat paired half-width. The bounded 32-run study does not establish a narrow
guarantee. The margins and procedure were not changed after observing results.

<details>
<summary>Per-replicate NLL summaries (nats/target)</summary>

Each row contains two independently randomized executions of the same fixed
16-target corpus. Values are rounded to 12 decimal places; the full-precision
records remain in the retained JSON.

| Run | Heterogeneous raw | Heterogeneous capped | Uniform raw | Uniform capped |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 12.482006293290 | 11.682122070606 | 10.016533512522 | 10.016533512522 |
| 1 | 11.461535531569 | 11.266993329209 | 8.943083382631 | 8.943083382631 |
| 2 | 11.750633367641 | 11.291147563174 | 10.074173559707 | 10.063701069066 |
| 3 | 12.883727636199 | 12.122482626103 | 8.864413440403 | 8.864413440403 |
| 4 | 12.580537802996 | 11.566792291204 | 9.518548294241 | 9.518548294241 |
| 5 | 12.588555088458 | 11.758572607338 | 9.463433976390 | 9.463433976390 |
| 6 | 12.498694581802 | 11.984188243728 | 9.241458833845 | 9.164778839213 |
| 7 | 12.413215564673 | 12.154105667979 | 9.554633515873 | 9.554633515873 |
| 8 | 12.106977243228 | 11.573760099617 | 10.008774641734 | 9.862967840302 |
| 9 | 11.043829233712 | 10.493976459289 | 9.374203569607 | 9.374203569607 |
| 10 | 13.126259343987 | 11.912805803816 | 9.973726116170 | 9.920691863505 |
| 11 | 11.702567701075 | 11.280907877364 | 9.516802389278 | 9.476188577041 |
| 12 | 13.322229386497 | 12.126833559768 | 9.741541385163 | 9.741541385163 |
| 13 | 12.910952594210 | 12.111857827026 | 9.484869467612 | 9.484869467612 |
| 14 | 12.530834365775 | 11.619199253928 | 9.707863280247 | 9.707863280247 |
| 15 | 12.891384325419 | 12.188785743503 | 9.515675012832 | 9.515675012832 |
| 16 | 11.544219405411 | 10.818480453549 | 9.298172988404 | 9.298172988404 |
| 17 | 11.895542026456 | 11.333822559054 | 9.602826286112 | 9.602826286112 |
| 18 | 12.794094229111 | 11.820389215528 | 9.227683006085 | 9.161284484030 |
| 19 | 12.219216387580 | 11.694296648851 | 10.013719317473 | 10.013719317473 |
| 20 | 12.565308395790 | 11.712832234666 | 9.080290265467 | 9.080290265467 |
| 21 | 12.002577471523 | 11.490977114143 | 9.610755032673 | 9.598361276596 |
| 22 | 11.940246095891 | 11.516121194785 | 9.730466847421 | 9.730466847421 |
| 23 | 11.475755620607 | 11.223669068530 | 9.573325048039 | 9.573325048039 |
| 24 | 13.483238022252 | 12.160123060995 | 9.765150850883 | 9.765150850883 |
| 25 | 11.910380817695 | 11.617372009273 | 9.404592236750 | 9.404592236750 |
| 26 | 12.103222811911 | 11.980481244687 | 9.321822755147 | 9.295020269854 |
| 27 | 12.715419629358 | 11.983320926591 | 9.318154058128 | 9.310707403661 |
| 28 | 12.137051072350 | 11.365622334116 | 9.528604060925 | 9.528604060925 |
| 29 | 11.756272879653 | 11.389555140761 | 9.734319929493 | 9.734319929493 |
| 30 | 12.649016051850 | 11.896062707750 | 9.414975088683 | 9.414975088683 |
| 31 | 12.590288104038 | 12.246312020397 | 8.903054605927 | 8.903054605927 |

</details>

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
forward/transfer overhead median was -15.68%; retain this noisy, small timing
sample as descriptive evidence, not a claim that observation makes execution
faster. Energy and physical-device performance were not measured.

Direct and observed logits matched exactly on all four documents. An independent
SciPy log-sum-exp calculation agreed with the loss evaluator. Both policy replay
checks passed. An independent audit verified all 64 unique parent streams,
replicate counts, execution order, target accounting, work equivalence, stored
file hashes, and the three interval calculations.

## Reproduce and inspect

The recorded environment was Linux x86_64, Python 3.12.10, JAX/JAXlib 0.10.2,
Equinox 0.13.8, NumPy 2.4.6, SciPy 1.18.1, tiktoken 0.14.0, and pinned Z1T 0.0.1.
The experiment used the verified source checkout through explicit `PYTHONPATH`
and the existing pinned dependency environment. It was not an installed-wheel
verification; release CI checks installed distributions separately.

Follow the [checkpoint setup](trained-checkpoint-verification.md), select the
source commit above, and run with the same CPU environment and a new output
directory:

```console
python -m tools.qualification.verify_trained_checkpoint /path/to/weights/model.eqx /path/to/new-run --policy-study
```

The command saves `protocol.json` before inference, then `load-and-smoke.json`
and `policy-results.json`, including per-replicate losses, timings and stream
identities. It refuses to overwrite an existing attempt. The retained run's
SHA-256 hashes are:

| File | SHA-256 |
| --- | --- |
| protocol.json | `52c183bf6182b5c868e361164d8b7b54dff9bb7792a48424a6991cdb4749414d` |
| load-and-smoke.json | `f6fb788dd9eb0bbcb81e5c5b37f28899d3a4af689ea8dfeaff9b34c4191b503a` |
| policy-results.json | `f0a94853dc24eabc9c4a7ba78a12f7c0951df57aadef019af84988ce9d5b62bc` |

Original per-unit records, environment, provenance and independent audit remain
in the maintainer's local evidence archive. Timing-dependent hashes will differ
on a rerun. Checkpoint weights are not redistributed.

## Decision

Complete the scoped experiment and report as evidence-only completion. Retain the
numerical reference and regression workflow; do not recommend the heterogeneous
policy or claim a successfully tuned deployment. A new policy, broader input
population, or materially higher precision would require a new frozen experiment
and resource decision. External invitations are excluded at the user's request.
