"""Four-city TSP as a QUBO: penalty certificate, exact oracle, diagnosed sampling.

The example compiles a distance matrix with a derived one-hot penalty and prints
the penalty certificate. It then enumerates all 2^16 states to find the exact
ground state and decodes it to a tour. Finally it runs a seeded Gibbs sampler,
decodes the best sample, and prints the mixing diagnostics for that run.

The sampler is the standard-library reference Gibbs sampler. Pass
``--backend thrml`` to use the optional THRML backend, which needs ``thrml`` and
``jax`` and takes tens of seconds to compile. This is a software demonstration only. It reports no
hardware speedup and no energy measurement.
"""

from __future__ import annotations

import argparse
import time
from collections import defaultdict

from gibbsiq import (
    ReferenceGibbsSampler,
    ReferenceSamplerConfig,
    SampleResult,
    SamplerConfig,
    THRMLSampler,
    compile_tsp,
    compute_diagnostics,
    exact_boltzmann_distribution,
)

distanceMatrix = ((0, 2, 9, 10), (2, 0, 6, 4), (9, 6, 0, 3), (10, 4, 3, 0))
knownOptimalLength = 18
seed = 7
numChains = 4
numReads = 400
beta = 1.0


def printSection(title: str) -> None:
    print(f"\n== {title} ==")


def describeEncoding(encoding) -> None:
    policy = encoding.penalty_policy
    model = encoding.ising_model
    print(f"penalty            : {policy.penalty} ({policy.selection})")
    print(f"strict boundary    : {policy.strict_boundary}")
    print(f"penalty status     : {policy.status}")
    print(f"variables          : {len(model.variables)}")
    print(f"quadratic terms    : {len(model.quadratic)}")
    print(f"offset             : {model.offset}")


def findExactGroundState(encoding):
    """Enumerate every state and return (spin state, total energy)."""
    model = encoding.ising_model
    distribution = exact_boltzmann_distribution(model, beta=1.0)
    bestIndex = max(range(len(distribution.states)), key=distribution.log_probabilities.__getitem__)
    state = distribution.states[bestIndex]
    return state, model.energy_from_spins(state), len(distribution.states)


def decodeSpinState(encoding, state) -> tuple[tuple[int, ...] | None, float | None]:
    sample = dict(zip(encoding.ising_model.variables, state))
    if not encoding.is_valid(sample, vartype="SPIN"):
        return None, None
    tour = encoding.decode(sample, vartype="SPIN")
    return tour, encoding.native_length(tour)


def runReferenceSampler(model):
    config = ReferenceSamplerConfig(
        beta=beta,
        n_warmup=300,
        steps_per_sample=2,
        num_chains=numChains,
        seed=seed,
    )
    raw = ReferenceGibbsSampler(config).sample(model, num_reads=numReads)
    samples = [dict(zip(raw.variables, state)) for state in raw.samples]
    result = SampleResult.from_model(model, samples, vartype="SPIN")
    grouped: dict[int, list[float]] = defaultdict(list)
    for chainId, energy in zip(raw.chain_ids, result.energies):
        grouped[chainId].append(energy)
    return result, [grouped[chainId] for chainId in sorted(grouped)]


def runThrmlSampler(model):
    """Optional backend. Needs thrml and jax; x64 keeps the audited logit error small."""
    import jax

    jax.config.update("jax_enable_x64", True)
    config = SamplerConfig(beta=beta, n_warmup=300, steps_per_sample=2, num_chains=numChains, seed=seed)
    result = THRMLSampler(config).sample(model, num_reads=numReads)
    return result, [list(chain) for chain in result.traces["energy"]]


def runSampler(model, backend: str):
    if backend == "thrml":
        return "THRMLSampler (JAX, x64)", *runThrmlSampler(model)
    return "ReferenceGibbsSampler (standard library)", *runReferenceSampler(model)


def bestValidTour(encoding, result):
    """Lowest-energy sample that decodes to a permutation, with its length."""
    ranked = sorted(range(len(result.samples)), key=result.energies.__getitem__)
    for index in ranked:
        tour, length = decodeSpinState(encoding, tuple(result.samples[index].values()))
        if tour is not None:
            return tour, length, result.energies[index]
    return None, None, None


def formatValue(value, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def printDiagnostics(diagnostics) -> None:
    energy = diagnostics["energy"]
    chains = diagnostics["chains"]
    print(
        f"energy ESS         : {formatValue(energy['ess'], 1)} of {energy['count']} draws ({energy['ess_status']})"
    )
    print(f"chain energy means : {[round(mean, 2) for mean in chains['chain_means']]}")
    print(f"split R-hat        : {formatValue(chains['rhat'])} ({chains['rhat_status']})")
    print(f"flags              : {', '.join(diagnostics['flags']) or 'none'}")
    if diagnostics["flags"]:
        print("reading            : the best sample is a valid optimum, but the flags say the chains")
        print("                     did not mix, so this run is not evidence of a converged distribution")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--backend", choices=("reference", "thrml"), default="reference")
    backendName = parser.parse_args(argv).backend

    printSection("1. Compile 4-city TSP")
    encoding = compile_tsp(distanceMatrix)
    describeEncoding(encoding)

    printSection("2. Exact ground state by enumeration")
    state, groundEnergy, stateCount = findExactGroundState(encoding)
    tour, length = decodeSpinState(encoding, state)
    print(f"states enumerated  : {stateCount}")
    print(f"ground energy      : {groundEnergy}")
    print(f"exact tour         : {'-'.join(map(str, tour))}")
    print(f"exact tour length  : {length:g}")
    print(f"matches known optimum {knownOptimalLength}: {length == knownOptimalLength}")

    printSection("3. Seeded Gibbs sampling")
    started = time.perf_counter()
    backend, result, chains = runSampler(encoding.ising_model, backendName)
    elapsed = time.perf_counter() - started
    sampledTour, sampledLength, sampledEnergy = bestValidTour(encoding, result)
    print(f"backend            : {backend}")
    print(f"seed / chains / reads: {seed} / {numChains} / {len(result.samples)}")
    print(f"sampling seconds   : {elapsed:.2f}")
    print(f"best sample energy : {sampledEnergy}")
    print(f"best sampled tour  : {'-'.join(map(str, sampledTour)) if sampledTour else 'none valid'}")
    print(f"best sampled length: {sampledLength}")
    print(f"reached exact optimum: {sampledEnergy is not None and sampledEnergy <= groundEnergy + 1e-9}")

    printSection("4. Mixing diagnostics")
    diagnostics = compute_diagnostics(
        energy_chains=chains,
        samples=result.samples,
        variables=result.variables,
    )
    printDiagnostics(diagnostics)


if __name__ == "__main__":
    main()
