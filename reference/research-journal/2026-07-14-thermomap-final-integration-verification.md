# 2026-07-14 - ThermoMap Analysis Tranche Final Integration Verification

## Paper Hook

Feeds the systems boundary, implementation-status, validity, and reproducibility sections: the
paper can cite this entry for the verified 40% equal-row ThermoMap score, the corrected
communication proxy semantics, and the independent evidence that closes the analysis tranche
without making a physical-TSU claim.

## Context And Outcome

The paper-grounded implementation tranche added target facts, stored-coefficient quantization,
exact small-law comparison, direct logical admissibility, supplied-partition chain analysis,
pairwise categorical/domain-wall lowering, a Potts objective evaluator, and an
optimization-only isoenergetic cluster move. Independent review then found an important defect
in the communication interpretation: on a $K_{5,5}$ supplied-partition case, the Aadit
paper-pair proxy was 18 while aggregate demand on a shared physical link was 50.

The defect was corrected before integration. The public result now keeps three distinct
algebraic quantities: the Aadit paper-pair proxy, the aggregate-link proxy, and the
max-composite proxy. Names and serialized interpretation text state that these are algebraic
serialization proxies, not measured latency, a feasible schedule, a hardware-frequency
limit, an energy value, or a mixing guarantee. A zero-traffic $K=400$ result is linear in the
number of partitions; dense active-route metadata remains worst-case $O(K^3)$.

The reviewed analysis APIs are exported by `gibbsiq.__init__` and exercised through a public
smoke path. The final repository run executed 457 tests in 120.615 seconds and returned `OK`.
The immutable pre-tranche Full ThermoMap baseline remains 6/20 = 30%; the verified current-tree
score is 8/20 = 40%. This is an equal-row capability rubric, not an effort-completion estimate.
The optimizer/audit foundation remains separately scored at 8.5/10 = 85%.

## Choices And Rejected Alternatives

1. **Preserve two score snapshots.** We retained 30% as the immutable pre-tranche baseline and
   recorded 40% as the verified current-tree score. We rejected rewriting the baseline because
   that would erase the measured delta and make a concurrent tranche grade itself retroactively.
2. **Keep equal-row scoring.** We retained the published `0/0.5/1` row rubric because the plan
   supplies no defensible effort weights. We rejected interpreting 40% as 40% of person-time;
   placement, routing, and calibration have substantially more risk than one row suggests.
3. **Separate communication quantities.** We report paper-pair, aggregate-link, and
   max-composite algebraic proxies separately. We rejected calling any of them latency,
   feasibility, a frequency bound, or a complete network model.
4. **Credit mapping search and cost algebra once each.** Small-$K$ supplied-partition order
   search earns half credit in placement/routing; the distinct algebraic communication output
   earns half credit in the parameterized cost row. We rejected additional credit for the
   Potts evaluator, exact verifier, categorical lowering, or ICM where their original component
   rows remain partial.
5. **Use fixed-configuration graph semantics.** At beta zero, the effective graph is edgeless
   while all variables and the original logical-edge count remain visible. We rejected deleting
   variables or treating the beta-zero certificate as valid for a later positive-beta/multi-beta
   schedule.
6. **Export the reviewed API surface.** Public package smoke tests cover the intended analysis
   path. We rejected silently integrating the optimization-only ICM primitive into equilibrium
   THRML sampling because its coupled replicas do not inherit independent-chain semantics.
7. **Borrow tests selectively.** Eighteen dependency-free dimod contracts retain Apache-2.0,
   commit, and file/line provenance; live dimod parity and ArviZ/R-`posterior` cross-checks remain
   independent anchors. We rejected copying unsupported DQM/CQM/serialization/sampler suites or
   tests that merely test upstream code.
8. **Classify Yao et al. as a baseline reference.** The sparse quantized simulated-bifurcation
   FPGA paper is a useful digital baseline/cost comparator. We rejected using it as TSU sampling
   evidence or porting its architecturally different dynamics into this tranche.

## Independent Audit Evidence

These checks were performed independently of the implementation's own returned summaries:

| Audit | Result |
| --- | --- |
| Communication defect reproduction | $K_{5,5}$ paper-pair proxy 18; aggregate-link and max-composite proxies 50. |
| Chain-order oracle | 170 exhaustive cases over $K=1\ldots6$ matched independent enumeration. |
| Corrected communication scouts | 200 random profiles matched the corrected algebra. The earlier pre-correction scout of 50 cases with all 24 permutations is retained as superseded negative evidence. |
| Zero-traffic storage | $K=400$ stores partition/link summaries linearly; no inactive pair-route expansion. |
| Fixed-beta-zero graphs | Every one of the 1,099 simple graphs with one to five vertices retained all variables, had zero effective edges/degree, one block, preserved the logical-edge count, and had exact-law TV error zero. |
| Exact/quantized laws | 120 random cases: maximum probability residual $5.55\times10^{-16}$; maximum analytic-bound residual zero. |
| ICM invariant | 2,501 move checks: maximum paired-energy residual $7.105\times10^{-15}$. |
| Domain-wall lowering | 60 models, 602 valid assignments, 2,223 encoded words: maximum valid-state energy error zero. |

The individual feature journals retain the exact formulas, fixtures, seeds where stochastic
generation was used, rejected parameters, and source-specific reproduction commands. This
entry does not invent a seed that was not present in the final integration report.

## Verification Commands And Environment

Recorded environment:

- Windows 11 (`Windows-11-10.0.26220-SP0`), AMD64;
- PowerShell;
- Python 3.13.5;
- repository root `E:\projects\Gibbsiq`;
- `PYTHONPATH=src` for tests and package smoke checks.

Final integration evidence:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s test_suite/tests
python -m ruff check .
python -m ruff format --check .
python -m mypy src/gibbsiq
python tools/check_markdown_math.py
```

Results:

- focused new-surface integration run: 114 tests passed;
- full discovery: 457 tests in 120.615 seconds, `OK`;
- Ruff lint: passed;
- Ruff format: 60 files already formatted;
- mypy: 19 source files, no issues;
- Markdown math: passed.

The root integrator owns the later final `git diff --check` after all concurrent documentation
edits stabilize; this entry does not claim that later tree state in advance.

## Artifact Identities

### Status and equation artifacts

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `reference/00-roadmap/thermomap-plan-status-2026-07-14.md` | 51,872 | `a40203c9cf31be2d4e948fd0a361514f8886801a2cfe0baea298917073900172` |
| `reference/08-evaluation/equation-audit.md` | 42,143 | `78427e2a0bd23c02a14cc103987eb0bad92f8a0e14efbf5c6421767cf5a290c5` |

### Primary papers

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `reference/01-architecture/papers/jelincic-2026-codon-optimization.pdf` | 2,081,289 | `81b73f3bc67e9b323b90cb27763701b7b529d2ee5fd753735464e4385b0066f9` |
| `reference/05-theory/papers/aadit-2026-million-pbit.pdf` | 25,492,691 | `56475ad7733bc5eb8e58e4435b7c549e2d1e26c76ede406d693c8c273949f268` |
| `reference/05-theory/papers/chowdhury-2025-adaptive-parallel-tempering-icm.pdf` | 16,392,886 | `e9a7eb2fb608b7ac8c8cc24284b0b3132392fdc83d09362b11df6eb0b0834cec` |
| `reference/01-architecture/papers/yao-2026-sparse-fpga-quantized-simulated-bifurcation.pdf` | 3,268,296 | `9d7adcb1f808bf7b046ae440fdafe54c2e84520c1a99e08b544a7181e0104fbd` |

The first three papers ground implemented analysis choices. Yao et al. is a digital FPGA
baseline/cost-model comparator, not TSU sampling evidence. A matching hash proves file identity,
not the truth or applicability of a paper claim.

### Integrated production surface

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `src/gibbsiq/__init__.py` | 3,461 | `77fe43b3bc4282813c310183beb3a8184212177af08af969064af36017c80497` |
| `src/gibbsiq/hardware.py` | 9,407 | `f794154f3039c702d5c0299f499057a4b331ed0e0015fc64103c8ad1a83e4a66` |
| `src/gibbsiq/exact_distribution.py` | 14,562 | `8ac3c13c3a3b7e3803bd17bff580c1a5004449f87e9e4dbab784d684bbc85c1a` |
| `src/gibbsiq/quantization.py` | 12,744 | `b2f0517bcf313936899f8324cbd4b56acfc5fd850068bed259433a70908793c2` |
| `src/gibbsiq/hardware_assessment.py` | 26,865 | `5297ce7a506b9cfc31000e19fb08e4a1a5148e54d7771f42703dff835374f4a3` |
| `src/gibbsiq/communication_profile.py` | 31,540 | `4de7c768aeb643b095ebc42ba98135ad8dda36c7f9dc22582357167c990ddaa9` |
| `src/gibbsiq/categorical.py` | 14,382 | `83878220a3548a87abf0be0409ab5a6a443d2223278bb8699a4213c2c38479b6` |
| `src/gibbsiq/domain_wall.py` | 17,178 | `b21f6ca6d8b69f76c37cae26385ee6b9b65c407d92482e9e4b2931e8daa359cf` |
| `src/gibbsiq/cluster_moves.py` | 11,238 | `3601cbdba2e4e0b998b34a566fe6f7de3159bddbe417d665c9c85c189965c1b9` |

### Direct integration tests

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `test_suite/tests/test_hardware_specs.py` | 7,377 | `13c1bf9fb6fe5959146364f6c3236bc09c9a5a12d99935df63ec4e6172f2b08f` |
| `test_suite/tests/test_exact_distribution.py` | 8,024 | `e73060027e3bac4ad4a840b59805353cb6b1ff7649785ff05225d08b274ada32` |
| `test_suite/tests/test_quantization.py` | 12,042 | `a57b6a1faac6b5446d4b0e05a03fa2d7242ce2afbd3738008220adbf792d24dc` |
| `test_suite/tests/test_hardware_assessment.py` | 20,706 | `e0f2c07afb88c14eff1404c23fd6925274de6d49c4bac67f8992c2c6b7c67cee` |
| `test_suite/tests/test_communication_profile.py` | 26,524 | `88f9c9274fab596193a83226f60fc4b02ab769205204533b132d259b89f188d6` |
| `test_suite/tests/test_categorical_model.py` | 9,493 | `d3a3322d36fab138a06bdac5ac10031b57dc42f9a1bce28206e5bfdde5408b52` |
| `test_suite/tests/test_domain_wall_encoding.py` | 16,833 | `6f2e18fa68058cf8e8a4c61f3fb534048de7b4874e443f83b52454789c0d00a6` |
| `test_suite/tests/test_cluster_moves.py` | 15,410 | `890a446c9d441fed547d6e1ed4b386fb85cd3bab48a9d4b3473654027a62c108` |
| `test_suite/tests/test_public_api_thermomap.py` | 6,831 | `9bf0d071731bc268558813db5fe8c74f619039e301a61e648a65b9b44b9a675a` |

Hashes capture the final-integration snapshot. Later edits require a new journal entry rather
than silently replacing these identities.

## Remaining Limitations

- No automatic partitioning, variable placement, degree-reduction transform, auxiliary route
  insertion, general-network router, or hybrid TSU/GPU partitioner exists.
- Exact order search is intentionally capped at $K\le6$; dense active-route metadata can remain
  cubic, and custom-object `repr` can make canonical label order process-specific.
- Communication outputs are not composed with `TSUSpec` provenance and are not calibrated
  time, frequency, energy, or schedule-feasibility predictions.
- The beta-zero assessment is fixed-configuration evidence, not a multi-beta portability
  certificate.
- Categorical valid-state energy equivalence does not prove encoded mixing, penalty adequacy,
  or categorical THRML execution.
- ICM is optimization-only and is not an equilibrium sampler or an integrated APT+ICM solver.
- No physical TSU result, TSU speedup, energy-per-independent-sample result, or competitive
  matched-budget optimization result was produced.

## Next Work

1. Implement categorical THRML conditionals and test empirical laws against exact categorical
   probabilities, including penalty sensitivity and invalid-wall behavior.
2. Generalize communication analysis to declared network topologies and stale/delayed boundary
   dynamics, with exact stationary-law error on small models.
3. Add automatic partitioning, placement, routing, and degree-reduction passes with independent
   witness and distribution oracles.
4. Build matched-budget classical baseline adapters. Use Yao et al. only as a digital
   comparator and borrow upstream test cases only when Gibbsiq exposes the same contract.
5. Compose calibrated cost provenance with observable-specific ESS before using the phrase
   thermodynamic roofline or reporting modeled ESS/joule.
