"""Generate deterministic exhaustive evidence for TM-LWR-001.

The generator independently evaluates the native objectives and expanded QUBO
coefficient tables. It does not call a lowering object's ``qubo_energy`` or
decoder while constructing oracle rows. Existing output is protected unless
``--overwrite`` is supplied deliberately.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.benchmark_bridge import candidate_from_result, compile_fixture, verify_optimum_claim  # noqa: E402
from gibbsiq.constraints import compile_knapsack, compile_tsp  # noqa: E402
from gibbsiq.factor_lowering import reduce_cubic_monomial  # noqa: E402
from gibbsiq.result import SampleResult  # noqa: E402

RUN_ID = "2026-07-23-lowering-contract"
SEED = 20_260_723
TOLERANCE = 1e-9
CUBIC_SENSITIVITY_MARGIN = 1e-6
DEFAULT_OUTPUT = REPO_ROOT / "reference" / "00-roadmap" / "artifacts" / "tm-lwr-001" / RUN_ID
SOURCE_PATHS = (
    "reference/08-evaluation/equation-audit.md",
    "src/gibbsiq/factor_lowering.py",
    "src/gibbsiq/constraints.py",
    "src/gibbsiq/benchmark_bridge.py",
    "src/gibbsiq/__init__.py",
    "test_suite/tests/test_factor_lowering.py",
    "test_suite/tests/test_constraints.py",
    "test_suite/tests/test_benchmark_bridge.py",
    "test_suite/tests/test_public_api_thermomap.py",
    "tools/generate_tm_lwr_001_artifacts.py",
)
ARTIFACT_FILENAMES = frozenset(
    {
        "generation-config.json",
        "environment.json",
        "cubic-enumeration.json",
        "knapsack-enumeration.json",
        "tsp-enumeration.json",
        "bridge-evidence.json",
        "source-files.json",
        "manifest.json",
    }
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_json_bytes(value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_existing_output(output: Path) -> None:
    if not output.is_dir():
        raise ValueError(f"artifact output must be a directory: {output}")
    unexpected = sorted(path.name for path in output.iterdir() if path.name not in ARTIFACT_FILENAMES)
    non_files = sorted(path.name for path in output.iterdir() if not path.is_file())
    if unexpected or non_files:
        raise ValueError(
            "refusing overwrite because the artifact directory has unexpected entries: "
            f"{sorted(set(unexpected + non_files))}"
        )


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _direct_qubo_energy(encoding: Any, bits: dict[object, int]) -> float:
    return math.fsum(
        [encoding.qubo_offset]
        + [encoding.qubo_linear[variable] * bits[variable] for variable in encoding.variables]
        + [
            coefficient * bits[left] * bits[right]
            for (left, right), coefficient in encoding.qubo_quadratic.items()
        ]
    )


def _direct_knapsack(
    weights: tuple[int, ...], values: tuple[int, ...], bits: tuple[int, ...]
) -> tuple[int, int]:
    return (
        sum(value * bit for value, bit in zip(values, bits)),
        sum(weight * bit for weight, bit in zip(weights, bits)),
    )


def _direct_one_hot(bits: tuple[int, ...], city_count: int) -> int:
    return sum(
        (1 - sum(bits[city * city_count + position] for city in range(city_count))) ** 2
        for position in range(city_count)
    ) + sum(
        (1 - sum(bits[city * city_count + position] for position in range(city_count))) ** 2
        for city in range(city_count)
    )


def _direct_tsp_length(matrix: list[list[int]], tour: tuple[int, ...]) -> int:
    return sum(matrix[tour[position]][tour[(position + 1) % len(tour)]] for position in range(len(tour)))


def _all_bits(size: int) -> Iterable[tuple[int, ...]]:
    return itertools.product((0, 1), repeat=size)


def _timed_compile(
    timings: dict[str, float],
    compiler: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    started = time.perf_counter()
    try:
        return compiler(*args, **kwargs)
    finally:
        timings["compile"] += time.perf_counter() - started


def _cubic_evidence(timings: dict[str, float]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for coefficient in (-2.0, 2.0):
        for penalty_name, penalty in (
            ("below", math.nextafter(abs(coefficient), -math.inf)),
            ("equal", abs(coefficient)),
            ("above", abs(coefficient) + CUBIC_SENSITIVITY_MARGIN),
        ):
            labels = ("left", ("middle", 4), b"right")
            offset = -1.75
            encoding = _timed_compile(
                timings,
                reduce_cubic_monomial,
                labels,
                coefficient=coefficient,
                penalty=penalty,
                offset=offset,
            )
            source_rows = []
            for source_bits in _all_bits(3):
                source = dict(zip(labels, source_bits))
                ancilla_rows = []
                for ancilla_bit in (0, 1):
                    bits = {**source, encoding.ancilla: ancilla_bit}
                    ancilla_rows.append(
                        {"ancilla": ancilla_bit, "qubo_energy": _direct_qubo_energy(encoding, bits)}
                    )
                expected = offset + coefficient * math.prod(source_bits)
                minimum_lowered_energy = min(row["qubo_energy"] for row in ancilla_rows)
                source_rows.append(
                    {
                        "source_bits": list(source_bits),
                        "source_energy": expected,
                        "minimum_lowered_energy": minimum_lowered_energy,
                        "minimizing_ancilla_count": sum(
                            row["qubo_energy"] == minimum_lowered_energy for row in ancilla_rows
                        ),
                        "ancilla_rows": ancilla_rows,
                    }
                )
            equality_error = max(
                abs(row["source_energy"] - row["minimum_lowered_energy"]) for row in source_rows
            )
            rows.append(
                {
                    "coefficient": coefficient,
                    "penalty_case": penalty_name,
                    "penalty_policy": encoding.penalty_policy.to_metadata(),
                    "maximum_energy_error": equality_error,
                    "rows": source_rows,
                }
            )
    one_ulp_encoding = _timed_compile(
        timings,
        reduce_cubic_monomial,
        ("left", ("middle", 4), b"right"),
        coefficient=2.0,
        penalty=math.nextafter(2.0, math.inf),
        offset=-1.75,
    )
    one_ulp_source = {"left": 1, ("middle", 4): 1, b"right": 1}
    one_ulp_energies = {
        str(ancilla): _direct_qubo_energy(
            one_ulp_encoding,
            {**one_ulp_source, one_ulp_encoding.ancilla: ancilla},
        )
        for ancilla in (0, 1)
    }
    one_ulp_probe = {
        "coefficient": 2.0,
        "penalty_policy": one_ulp_encoding.penalty_policy.to_metadata(),
        "source_bits": [1, 1, 1],
        "ancilla_energies": one_ulp_energies,
        "energy_difference": one_ulp_energies["0"] - one_ulp_energies["1"],
        "observed_binary64_tie": one_ulp_energies["0"] == one_ulp_energies["1"],
        "interpretation": (
            "negative numerical result: a one-ULP strict exact-arithmetic margin did not "
            "produce an observed binary64 ancilla-energy separation"
        ),
    }
    return {
        "oracle": "direct source monomial and direct exposed QUBO coefficient summation",
        "finite_sensitivity_margin": CUBIC_SENSITIVITY_MARGIN,
        "rows": rows,
        "binary64_one_ulp_probe": one_ulp_probe,
        "passed": all(
            (
                row["penalty_case"] == "below"
                and row["penalty_policy"]["status"] == "inadequate"
                and row["maximum_energy_error"] > 0.0
            )
            or (
                row["penalty_case"] == "equal"
                and row["penalty_policy"]["status"] == "adequate_at_energy_boundary"
                and row["maximum_energy_error"] <= TOLERANCE
                and any(source["minimizing_ancilla_count"] > 1 for source in row["rows"])
            )
            or (
                row["penalty_case"] == "above"
                and row["penalty_policy"]["status"] == "proved_ancilla_unique"
                and row["maximum_energy_error"] <= TOLERANCE
                and all(source["minimizing_ancilla_count"] == 1 for source in row["rows"])
            )
            for row in rows
        )
        and one_ulp_probe["observed_binary64_tie"],
    }


def _knapsack_rows(
    weights: tuple[int, ...],
    values: tuple[int, ...],
    capacity: int,
    *,
    penalty: float,
    offset: float,
    timings: dict[str, float],
) -> dict[str, Any]:
    encoding = _timed_compile(
        timings,
        compile_knapsack,
        weights,
        values,
        capacity,
        penalty=penalty,
        offset=offset,
    )
    rows = []
    source_minimum = math.inf
    lowered_minimum = math.inf
    infeasible_minima: list[float] = []
    for item_bits in _all_bits(len(weights)):
        value, weight = _direct_knapsack(weights, values, item_bits)
        source = dict(zip(encoding.item_variables, item_bits))
        word_rows = []
        for slack_bits in _all_bits(len(encoding.slack_variables)):
            bits = {**source, **dict(zip(encoding.slack_variables, slack_bits))}
            slack = sum(coefficient * bit for coefficient, bit in zip(encoding.slack_weights, slack_bits))
            word_rows.append(
                {
                    "slack_bits": list(slack_bits),
                    "slack": slack,
                    "residual": weight + slack - capacity,
                    "qubo_energy": _direct_qubo_energy(encoding, bits),
                }
            )
        lowered = min(row["qubo_energy"] for row in word_rows)
        lowered_minimum = min(lowered_minimum, lowered)
        if weight <= capacity:
            source_energy = offset - encoding.reward_scale * value + weight
            source_minimum = min(source_minimum, source_energy)
        else:
            source_energy = None
            infeasible_minima.append(lowered)
        rows.append(
            {
                "item_bits": list(item_bits),
                "native_value": value,
                "native_weight": weight,
                "source_energy_if_feasible": source_energy,
                "minimum_lowered_energy": lowered,
                "slack_rows": word_rows,
            }
        )
    return {
        "input": {"weights": list(weights), "values": list(values), "capacity": capacity, "offset": offset},
        "penalty_policy": encoding.penalty_policy.to_metadata(),
        "rows": rows,
        "native_feasible_minimum": source_minimum,
        "lowered_minimum": lowered_minimum,
        "infeasible_above_native_minimum": all(value > source_minimum for value in infeasible_minima),
        "passed": lowered_minimum == source_minimum
        and all(value > source_minimum for value in infeasible_minima),
    }


def _knapsack_evidence(timings: dict[str, float]) -> dict[str, Any]:
    weights = (2, 3, 4)
    values = (4, 5, 7)
    capacity = 5
    boundary = max((capacity + 1) * value - weight for weight, value in zip(weights, values))
    main = _knapsack_rows(
        weights,
        values,
        capacity,
        penalty=float(boundary + 1),
        offset=-2.5,
        timings=timings,
    )
    boundary_rows = {
        name: _knapsack_rows(
            (2,),
            (2,),
            1,
            penalty=penalty,
            offset=0.0,
            timings=timings,
        )
        for name, penalty in (
            ("below", math.nextafter(2.0, -math.inf)),
            ("equal", 2.0),
            ("above", math.nextafter(2.0, math.inf)),
        )
    }
    below = boundary_rows["below"]
    equal = boundary_rows["equal"]
    above = boundary_rows["above"]
    metamorphic = _knapsack_rows(
        (4, 6, 8),
        (8, 10, 14),
        10,
        penalty=147.0,
        offset=9.5,
        timings=timings,
    )
    return {
        "oracle": "direct native value/weight enumeration and direct exposed QUBO coefficient summation",
        "main": main,
        "boundary_cases": boundary_rows,
        "metamorphic_scale_offset_case": metamorphic,
        "passed": (
            main["passed"]
            and below["penalty_policy"]["status"] == "not_proved_adequate"
            and below["lowered_minimum"] < below["native_feasible_minimum"]
            and equal["penalty_policy"]["status"] == "not_proved_adequate"
            and equal["lowered_minimum"] == equal["native_feasible_minimum"]
            and not equal["infeasible_above_native_minimum"]
            and above["penalty_policy"]["status"] == "proved_adequate"
            and above["passed"]
            and metamorphic["passed"]
        ),
    }


def _tsp_rows(
    matrix: list[list[int]],
    *,
    penalty: float,
    offset: float,
    timings: dict[str, float],
) -> dict[str, Any]:
    encoding = _timed_compile(
        timings,
        compile_tsp,
        matrix,
        penalty=penalty,
        offset=offset,
    )
    rows = []
    valid_energies = []
    all_energies = []
    invalid_energies = []
    invalid_violations = []
    city_count = len(matrix)
    for word in _all_bits(len(encoding.variables)):
        bits = dict(zip(encoding.variables, word))
        violation = _direct_one_hot(word, city_count)
        energy = _direct_qubo_energy(encoding, bits)
        all_energies.append(energy)
        row: dict[str, Any] = {
            "bits": list(word),
            "one_hot_violation": violation,
            "qubo_energy": energy,
        }
        if violation == 0:
            tour = tuple(
                next(city for city in range(city_count) if word[city * city_count + position] == 1)
                for position in range(city_count)
            )
            row["tour"] = list(tour)
            row["native_length"] = _direct_tsp_length(matrix, tour)
            valid_energies.append(energy)
        else:
            invalid_violations.append(violation)
            invalid_energies.append(energy)
        rows.append(row)
    return {
        "input": {"distance_matrix": matrix, "offset": offset},
        "penalty_policy": encoding.penalty_policy.to_metadata(),
        "rows": rows,
        "minimum_all_energy": min(all_energies),
        "minimum_valid_energy": min(valid_energies),
        "minimum_invalid_energy": min(invalid_energies),
        "minimum_invalid_one_hot_violation": min(invalid_violations),
        "passed": min(all_energies) == min(valid_energies) and min(invalid_violations) >= 2,
    }


def _tsp_evidence(timings: dict[str, float]) -> dict[str, Any]:
    matrix = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
    main = _tsp_rows(matrix, penalty=2.0, offset=3.25, timings=timings)
    boundary_cases = {
        name: _tsp_rows(matrix, penalty=penalty, offset=3.25, timings=timings)
        for name, penalty in (
            ("below", math.nextafter(1.0, -math.inf)),
            ("equal", 1.0),
            ("above", math.nextafter(1.0, math.inf)),
        )
    }
    below = boundary_cases["below"]
    equal = boundary_cases["equal"]
    above = boundary_cases["above"]
    metamorphic = _tsp_rows(
        [[2 * value for value in row] for row in matrix],
        penalty=3.0,
        offset=-4.0,
        timings=timings,
    )
    return {
        "oracle": "direct two-way-one-hot enumeration and native cyclic tour-length evaluation",
        "main": main,
        "boundary_cases": boundary_cases,
        "metamorphic_scale_offset_case": metamorphic,
        "passed": (
            main["passed"]
            and below["penalty_policy"]["status"] == "not_proved_adequate"
            and below["minimum_invalid_energy"] < below["minimum_valid_energy"]
            and equal["penalty_policy"]["status"] == "not_proved_adequate"
            and equal["minimum_invalid_energy"] == equal["minimum_valid_energy"]
            and above["penalty_policy"]["status"] == "proved_adequate"
            and above["minimum_invalid_energy"] > above["minimum_valid_energy"]
            and metamorphic["passed"]
        ),
    }


def _slack_bits(weights: tuple[int, ...], target: int) -> tuple[int, ...]:
    return next(
        bits
        for bits in _all_bits(len(weights))
        if sum(weight * bit for weight, bit in zip(weights, bits)) == target
    )


def _bridge_evidence(timings: dict[str, float]) -> dict[str, Any]:
    corpus = json.loads(
        (REPO_ROOT / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json").read_text(
            encoding="utf-8"
        )
    )
    fixtures = {
        fixture["family"]: fixture
        for fixture in corpus["fixtures"]
        if fixture["family"] in {"knapsack", "tsp"}
    }
    rows = []
    for family in ("knapsack", "tsp"):
        fixture = fixtures[family]
        fixture_input_only = {key: value for key, value in fixture.items() if key != "expected"}
        model = _timed_compile(timings, compile_fixture, fixture_input_only)
        if family == "knapsack":
            weights = tuple(fixture_input_only["input"]["weights"])
            values = tuple(fixture_input_only["input"]["values"])
            capacity = fixture_input_only["input"]["capacity"]
            native_rows = []
            for bits in _all_bits(len(weights)):
                native_evaluation = _direct_knapsack(weights, values, bits)
                if native_evaluation[1] <= capacity:
                    native_rows.append((native_evaluation, bits))
            (value, weight), item_bits = min(native_rows, key=lambda item: (-item[0][0], item[0][1], item[1]))
            slack_weights = tuple(
                1
                if index == 0
                else capacity - ((1 << index) - 1)
                if index == len(model.variables) - len(weights) - 1
                else 1 << index
                for index in range(len(model.variables) - len(weights))
            )
            slack = _slack_bits(slack_weights, capacity - weight)
            sample = dict(zip(model.variables, item_bits + slack))
            result = SampleResult.from_model(model, [sample], vartype="BINARY")
            candidate = candidate_from_result(fixture_input_only, result)
            strict_differences = verify_optimum_claim(fixture, candidate)
            rows.append(
                {
                    "fixture_id": fixture["id"],
                    "family": family,
                    "input_only": True,
                    "native_exhaustive_assignment_count": len(native_rows),
                    "native_value": value,
                    "native_weight": weight,
                    "candidate": candidate,
                    "strict_oracle_differences": strict_differences,
                    "candidate_matches_native": (
                        candidate["max_value"] == value and candidate["weight_at_optimum"] == weight
                    ),
                }
            )
        else:
            matrix = fixture_input_only["input"]["distance_matrix"]
            city_count = fixture_input_only["input"]["num_cities"]
            tours = itertools.permutations(range(1, city_count))
            tour = min(
                ((0,) + permutation for permutation in tours),
                key=lambda candidate: (_direct_tsp_length(matrix, candidate), candidate),
            )
            bits = [0] * len(model.variables)
            for position, city in enumerate(tour):
                bits[city * city_count + position] = 1
            result = SampleResult.from_model(model, [dict(zip(model.variables, bits))], vartype="BINARY")
            candidate = candidate_from_result(fixture_input_only, result)
            native_length = _direct_tsp_length(matrix, tour)
            strict_differences = verify_optimum_claim(fixture, candidate)
            rows.append(
                {
                    "fixture_id": fixture["id"],
                    "family": family,
                    "input_only": True,
                    "native_exhaustive_assignment_count": math.factorial(city_count - 1),
                    "native_length": native_length,
                    "candidate": candidate,
                    "strict_oracle_differences": strict_differences,
                    "candidate_matches_native": candidate["optimal_tour_length"] == native_length,
                }
            )
    return {
        "oracle": "native enumeration and candidate construction from fixture input with expected removed",
        "rows": rows,
        "passed": all(
            row["input_only"] and row["candidate_matches_native"] and not row["strict_oracle_differences"]
            for row in rows
        ),
    }


def generate(output: Path, *, overwrite: bool) -> None:
    wall_start = time.perf_counter()
    output_preexisted = output.exists()
    if output.exists():
        if not overwrite:
            raise FileExistsError(f"refusing to overwrite artifact directory: {output}")
        _validate_existing_output(output)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
    timings = {"compile": 0.0}
    oracle_start = time.perf_counter()
    cubic = _cubic_evidence(timings)
    knapsack = _knapsack_evidence(timings)
    tsp = _tsp_evidence(timings)
    bridge = _bridge_evidence(timings)
    evidence_seconds = time.perf_counter() - oracle_start
    if not all((cubic["passed"], knapsack["passed"], tsp["passed"], bridge["passed"])):
        raise AssertionError("one or more independent evidence checks failed")
    config = {
        "task_id": "TM-LWR-001",
        "run_id": RUN_ID,
        "generator_seed": SEED,
        "rng": "not applicable; all cases are fixed deterministic enumerations",
        "absolute_tolerance": TOLERANCE,
        "reproduction_command": "python tools/generate_tm_lwr_001_artifacts.py --overwrite",
        "oracle": "direct native objectives plus direct QUBO coefficient summation outside lowering methods",
        "classification": {
            "penalty_bounds": "derived exact finite-state sufficient certificates",
            "hardware_values": "not applicable",
            "sampling_claim": "none",
        },
        "timing_boundaries": {
            "compile": (
                "production lowering and fixture-compilation calls invoked directly by this "
                "generator; the bridge's intentional input-only recompilation is included in "
                "native_oracle_and_bridge_validation"
            ),
            "wall_clock": (
                "generator entry through staging every substantive evidence payload; final "
                "environment/manifest serialization and manifest-last publication are excluded"
            ),
        },
    }
    source_rows = [
        {
            "path": relative_path,
            "bytes": (REPO_ROOT / relative_path).stat().st_size,
            "sha256": _sha256(REPO_ROOT / relative_path),
        }
        for relative_path in SOURCE_PATHS
    ]
    substantive_files = {
        "generation-config.json": config,
        "cubic-enumeration.json": cubic,
        "knapsack-enumeration.json": knapsack,
        "tsp-enumeration.json": tsp,
        "bridge-evidence.json": bridge,
        "source-files.json": {"algorithm": "SHA-256", "files": source_rows},
    }
    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as stage_name:
        stage = Path(stage_name)
        for filename, payload in substantive_files.items():
            _write_json(stage / filename, payload)
        environment = {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "os_name": os.name,
            "git_head": _git_head(),
            "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
            "timing_seconds": {
                "compile": timings["compile"],
                "native_oracle_and_bridge_validation": max(
                    0.0,
                    evidence_seconds - timings["compile"],
                ),
                "sample": 0.0,
                "diagnostics": 0.0,
                "tuning": 0.0,
                "wall_clock": time.perf_counter() - wall_start,
            },
        }
        files = {**substantive_files, "environment.json": environment}
        _write_json(stage / "environment.json", environment)
        manifest = {
            "task_id": "TM-LWR-001",
            "run_id": RUN_ID,
            "algorithm": "SHA-256",
            "files": [
                {
                    "path": filename,
                    "bytes": (stage / filename).stat().st_size,
                    "sha256": _sha256(stage / filename),
                }
                for filename in sorted(files)
            ],
        }
        _write_json(stage / "manifest.json", manifest)

        if output_preexisted:
            if not output.exists():
                raise FileNotFoundError(f"artifact directory disappeared before publication: {output}")
            _validate_existing_output(output)
        else:
            output.mkdir(exist_ok=False)
        for filename in sorted(files):
            os.replace(stage / filename, output / filename)
        # A partial publication cannot retain a matching manifest: publish it last.
        os.replace(stage / "manifest.json", output / "manifest.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args()
    output = arguments.out if arguments.out.is_absolute() else REPO_ROOT / arguments.out
    generate(output.resolve(), overwrite=arguments.overwrite)


if __name__ == "__main__":
    main()
