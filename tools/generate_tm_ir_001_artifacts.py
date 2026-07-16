"""Generate deterministic TM-IR-001 projection and serialization evidence."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import (  # noqa: E402
    PROGRAM_SCHEMA_VERSION,
    CategoricalModel,
    IsingModel,
    ThermodynamicProgram,
    __version__,
)

RUN_ID = "2026-07-15-program-envelope"
SEED = 20_260_715
ABSOLUTE_TOLERANCE = 1e-9
ISING_CASE_COUNT = 24
CATEGORICAL_CASE_COUNT = 18
DEFAULT_OUTPUT = REPO_ROOT / "reference" / "00-roadmap" / "artifacts" / "tm-ir-001" / RUN_ID
SOURCE_PATHS = (
    "reference/08-evaluation/equation-audit.md",
    "src/gibbsiq/__init__.py",
    "src/gibbsiq/categorical.py",
    "src/gibbsiq/model.py",
    "src/gibbsiq/program.py",
    "src/gibbsiq/result.py",
    "test_suite/tests/test_public_api_thermomap.py",
    "test_suite/tests/test_thermodynamic_program.py",
    "tools/generate_tm_ir_001_artifacts.py",
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


def _git_value(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _assignments(model: IsingModel | CategoricalModel) -> Iterable[dict[Any, Any]]:
    if isinstance(model, IsingModel):
        domains: list[Sequence[Any]] = [(-1, 1) for _ in model.variables]
    else:
        domains = [model.domains[variable] for variable in model.variables]
    for values in itertools.product(*domains):
        yield dict(zip(model.variables, values))


def _direct_energy(program: ThermodynamicProgram, free_assignment: Mapping[Any, Any]) -> float:
    complete = {
        variable: (
            program.clamp_values[variable] if variable in program.clamp_values else free_assignment[variable]
        )
        for variable in program.model.variables
    }
    model = program.model
    if isinstance(model, IsingModel):
        terms = [model.offset]
        terms.extend(model.linear[variable] * complete[variable] for variable in model.variables)
        terms.extend(
            coefficient * complete[left] * complete[right]
            for (left, right), coefficient in model.quadratic.items()
        )
        return math.fsum(terms)
    terms = [model.offset]
    terms.extend(model.unary[variable][complete[variable]] for variable in model.variables)
    terms.extend(table[(complete[left], complete[right])] for (left, right), table in model.pairwise.items())
    return math.fsum(terms)


def _assignment_row(model: IsingModel | CategoricalModel, assignment: Mapping[Any, Any]) -> list[Any]:
    return [assignment[variable] for variable in model.variables]


def _expected_lineage_destinations(
    program: ThermodynamicProgram,
) -> dict[str, dict[str, Any]]:
    """Derive destination records without consuming projection metadata."""
    source_positions = {variable: position for position, variable in enumerate(program.model.variables)}
    target_positions = {variable: position for position, variable in enumerate(program.free_variables)}
    free = set(program.free_variables)
    expected: dict[str, dict[str, Any]] = {}
    pairs: Iterable[tuple[Any, Any]]
    if isinstance(program.model, IsingModel):
        for variable in program.model.variables:
            factor_id = f"linear:{source_positions[variable]}"
            expected[factor_id] = (
                {"target_kind": "linear", "variable_position": target_positions[variable]}
                if variable in free
                else {"target_kind": "offset"}
            )
        pair_prefix = "quadratic"
        pair_kind = "quadratic"
        unary_kind = "linear"
        pairs = program.model.quadratic
    else:
        for variable in program.model.variables:
            factor_id = f"unary:{source_positions[variable]}"
            expected[factor_id] = (
                {"target_kind": "unary", "variable_position": target_positions[variable]}
                if variable in free
                else {"target_kind": "offset"}
            )
        pair_prefix = "pairwise"
        pair_kind = "pairwise"
        unary_kind = "unary"
        pairs = program.model.pairwise

    for left, right in pairs:
        factor_id = f"{pair_prefix}:{source_positions[left]}:{source_positions[right]}"
        if left in free and right in free:
            expected[factor_id] = {
                "target_kind": pair_kind,
                "left_position": target_positions[left],
                "right_position": target_positions[right],
            }
        elif left in free or right in free:
            survivor = left if left in free else right
            expected[factor_id] = {
                "target_kind": unary_kind,
                "variable_position": target_positions[survivor],
            }
        else:
            expected[factor_id] = {"target_kind": "offset"}
    return expected


def _lineage_is_valid(
    program: ThermodynamicProgram,
    projected: IsingModel | CategoricalModel,
) -> bool:
    transformations = projected.metadata["thermodynamic_projection"]["transformations"]
    expected = _expected_lineage_destinations(program)
    if len(transformations) != len(expected):
        return False
    by_factor: dict[str, Mapping[str, Any]] = {}
    for row in transformations:
        factor_id = row.get("factor_id")
        if not isinstance(factor_id, str) or factor_id in by_factor:
            return False
        by_factor[factor_id] = row
    if set(by_factor) != set(expected) or set(expected) != set(program.factor_sources):
        return False
    for factor_id, expected_target in expected.items():
        row = by_factor[factor_id]
        if row.get("source_id") != program.factor_sources[factor_id]:
            return False
        observed_target = {key: row[key] for key in expected_target if key in row}
        if observed_target != expected_target:
            return False
        allowed = {"factor_id", "source_id", *expected_target}
        if set(row) != allowed:
            return False
    return True


def _case_record(case_id: str, program: ThermodynamicProgram) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = program.to_dict()
    json_payload = json.loads(json.dumps(payload, sort_keys=True, allow_nan=False))
    restored = ThermodynamicProgram.from_dict(json_payload)
    serialization_equal = restored.to_dict() == payload
    projected = program.project()
    rows: list[dict[str, Any]] = []
    maximum_error = 0.0
    for assignment in _assignments(projected):
        expected = _direct_energy(program, assignment)
        actual = projected.energy(assignment)
        error = abs(expected - actual)
        maximum_error = max(maximum_error, error)
        rows.append(
            {
                "free_assignment_values": _assignment_row(projected, assignment),
                "source_energy": expected,
                "projected_energy": actual,
                "absolute_error": error,
            }
        )
    lineage_valid = _lineage_is_valid(program, projected)
    passed = serialization_equal and lineage_valid and maximum_error <= ABSOLUTE_TOLERANCE
    fixture = {
        "case_id": case_id,
        "model_kind": "ising" if isinstance(program.model, IsingModel) else "categorical",
        "free_variable_count": len(program.free_variables),
        "clamped_variable_count": len(program.clamped_variables),
        "source_program": payload,
        "projected_model": ThermodynamicProgram(projected).to_dict()["model"],
        "enumerated_rows": rows,
    }
    result = {
        "case_id": case_id,
        "enumerated_assignment_count": len(rows),
        "maximum_absolute_energy_error": maximum_error,
        "serialization_round_trip_equal": serialization_equal,
        "lineage_destinations_valid": lineage_valid,
        "passed": passed,
    }
    return fixture, result


def _coefficient(rng: random.Random, *, denominator: int = 4) -> float:
    return rng.randint(-8, 8) / denominator


def _with_sources(
    model: IsingModel | CategoricalModel,
    *,
    clamps: Mapping[Any, Any],
    coordinates: Mapping[Any, tuple[float, float]],
    observations: Mapping[Any, Any],
    case_id: str,
) -> ThermodynamicProgram:
    preliminary = ThermodynamicProgram(model)
    sources = {factor_id: f"fixture:{case_id}:{factor_id}" for factor_id in preliminary.factor_sources}
    return ThermodynamicProgram(
        model,
        clamps=clamps,
        coordinates=coordinates,
        observations=observations,
        factor_sources=sources,
        metadata={"case_id": case_id, "generator_seed": SEED},
    )


def _random_ising_programs(rng: random.Random) -> list[tuple[str, ThermodynamicProgram]]:
    programs: list[tuple[str, ThermodynamicProgram]] = []
    for case_index in range(ISING_CASE_COUNT):
        case_id = f"ising-{case_index:02d}"
        variable_count = rng.randint(1, 5)
        variables = tuple(f"s{case_index}_{position}" for position in range(variable_count))
        linear = {variable: _coefficient(rng) for variable in variables}
        quadratic: dict[tuple[str, str], float] = {}
        for left_position in range(variable_count):
            for right_position in range(left_position + 1, variable_count):
                if rng.random() < 0.55:
                    coefficient = _coefficient(rng)
                    if coefficient != 0.0:
                        quadratic[(variables[left_position], variables[right_position])] = coefficient
        model = IsingModel(
            variables=variables,
            linear=linear,
            quadratic=quadratic,
            offset=_coefficient(rng),
            metadata={"fixture_family": "random-ising", "case_index": case_index},
        )
        clamp_count = rng.randint(0, variable_count)
        clamped = set(rng.sample(list(variables), clamp_count))
        clamps = {variable: rng.choice((-1, 1)) for variable in variables if variable in clamped}
        observations = {
            variable: {"source": "fixture", "observed_spin": value} for variable, value in clamps.items()
        }
        coordinates = {
            variable: (float(position), float(case_index)) for position, variable in enumerate(variables)
        }
        programs.append(
            (
                case_id,
                _with_sources(
                    model,
                    clamps=clamps,
                    coordinates=coordinates,
                    observations=observations,
                    case_id=case_id,
                ),
            )
        )
    return programs


def _random_categorical_programs(
    rng: random.Random,
) -> list[tuple[str, ThermodynamicProgram]]:
    programs: list[tuple[str, ThermodynamicProgram]] = []
    for case_index in range(CATEGORICAL_CASE_COUNT):
        case_id = f"categorical-{case_index:02d}"
        variable_count = rng.randint(1, 4)
        variables = tuple(f"x{case_index}_{position}" for position in range(variable_count))
        domains = {variable: tuple(range(rng.randint(2, 3))) for variable in variables}
        unary = {
            variable: {category: _coefficient(rng, denominator=2) for category in domains[variable]}
            for variable in variables
        }
        pairwise: dict[tuple[str, str], dict[tuple[int, int], float]] = {}
        for left_position in range(variable_count):
            for right_position in range(left_position + 1, variable_count):
                if rng.random() >= 0.5:
                    continue
                left = variables[left_position]
                right = variables[right_position]
                canonical = {
                    (left_category, right_category): _coefficient(rng, denominator=2)
                    for left_category in domains[left]
                    for right_category in domains[right]
                }
                if rng.random() < 0.5:
                    pairwise[(right, left)] = {
                        (right_category, left_category): canonical[(left_category, right_category)]
                        for right_category in domains[right]
                        for left_category in domains[left]
                    }
                else:
                    pairwise[(left, right)] = canonical
        model = CategoricalModel(
            variables=variables,
            domains=domains,
            unary=unary,
            pairwise=pairwise,
            offset=_coefficient(rng, denominator=2),
            metadata={"fixture_family": "random-categorical", "case_index": case_index},
        )
        clamp_count = rng.randint(0, variable_count)
        clamped = set(rng.sample(list(variables), clamp_count))
        clamps = {variable: rng.choice(domains[variable]) for variable in variables if variable in clamped}
        observations = {
            variable: {"source": "fixture", "observed_category": value} for variable, value in clamps.items()
        }
        coordinates = {
            variable: (float(position), float(case_index)) for position, variable in enumerate(variables)
        }
        programs.append(
            (
                case_id,
                _with_sources(
                    model,
                    clamps=clamps,
                    coordinates=coordinates,
                    observations=observations,
                    case_id=case_id,
                ),
            )
        )
    return programs


def _serialization_examples() -> list[dict[str, Any]]:
    tuple_label = ("node", 1)
    bytes_label = b"node-2"
    ising = ThermodynamicProgram(
        IsingModel(
            variables=(tuple_label, bytes_label),
            linear={tuple_label: 0.5, bytes_label: -0.75},
            quadratic={(tuple_label, bytes_label): 1.25},
            offset=-2.0,
            metadata={"labels": "tuple-and-bytes"},
        ),
        clamps={bytes_label: -1},
        observations={bytes_label: {"raw": b"observed"}},
    )
    categorical_model = CategoricalModel(
        variables=("left", "right"),
        domains={"left": (0, 1), "right": ("off", "on")},
        pairwise={
            ("right", "left"): {
                (right, left): float(left + (2 if right == "on" else 0))
                for right in ("off", "on")
                for left in (0, 1)
            }
        },
        offset=-0.75,
    )
    categorical = ThermodynamicProgram(categorical_model, clamps={"right": "on"})
    examples = []
    for case_id, program in (("typed-ising", ising), ("reversed-categorical", categorical)):
        payload = program.to_dict()
        restored = ThermodynamicProgram.from_dict(json.loads(json.dumps(payload, allow_nan=False)))
        examples.append(
            {
                "case_id": case_id,
                "payload": payload,
                "round_trip_equal": restored.to_dict() == payload,
            }
        )
    return examples


def generate(output: Path, *, overwrite: bool) -> None:
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise FileExistsError(f"artifact directory already contains files: {output}")
    output.mkdir(parents=True, exist_ok=True)
    wall_start = time.perf_counter()
    rng = random.Random(SEED)

    compile_start = time.perf_counter()
    programs = _random_ising_programs(rng) + _random_categorical_programs(rng)
    compile_seconds = time.perf_counter() - compile_start

    verification_start = time.perf_counter()
    fixtures: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for case_id, program in programs:
        fixture, result = _case_record(case_id, program)
        fixtures.append(fixture)
        results.append(result)
    serialization_examples = _serialization_examples()
    verification_seconds = time.perf_counter() - verification_start

    if not all(result["passed"] for result in results):
        raise AssertionError("at least one independent projection case failed")
    if not all(example["round_trip_equal"] for example in serialization_examples):
        raise AssertionError("at least one serialization fixture failed to round trip")

    configuration = {
        "task_id": "TM-IR-001",
        "run_id": RUN_ID,
        "program_schema_version": PROGRAM_SCHEMA_VERSION,
        "generator_seed": SEED,
        "rng": "Python random.Random (MT19937)",
        "absolute_tolerance": ABSOLUTE_TOLERANCE,
        "relative_tolerance": 0.0,
        "ising_case_count": ISING_CASE_COUNT,
        "categorical_case_count": CATEGORICAL_CASE_COUNT,
        "ising_variable_count_range": [1, 5],
        "categorical_variable_count_range": [1, 4],
        "categorical_domain_size_range": [2, 3],
        "oracle": (
            "enumerate free assignments, merge original clamps, and independently sum the "
            "original offset/unary/pair factors without model.energy or program.project"
        ),
        "reproduction_command": (
            "& .venv/Scripts/python.exe tools/generate_tm_ir_001_artifacts.py --overwrite"
        ),
        "classification": {
            "seed": "declared deterministic fixture input",
            "tolerance": "assumed project-wide floating comparison tolerance from CLAUDE.md",
            "energies": "computed",
            "hardware_values": "not applicable",
        },
    }
    environment = {
        "task_id": "TM-IR-001",
        "run_id": RUN_ID,
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "os_name": os.name,
        "gibbsiq_version": __version__,
        "git_head": _git_value("rev-parse", "HEAD"),
        "timing_seconds": {
            "compile_fixture_programs": compile_seconds,
            "projection_serialization_and_oracle": verification_seconds,
            "sample": 0.0,
            "diagnostics": 0.0,
            "tuning": 0.0,
            "wall_before_artifact_writes": time.perf_counter() - wall_start,
        },
    }
    projection_payload = {
        "task_id": "TM-IR-001",
        "run_id": RUN_ID,
        "oracle_tolerance": ABSOLUTE_TOLERANCE,
        "cases": fixtures,
    }
    result_payload = {
        "task_id": "TM-IR-001",
        "run_id": RUN_ID,
        "case_count": len(results),
        "total_enumerated_assignment_count": sum(result["enumerated_assignment_count"] for result in results),
        "maximum_absolute_energy_error": max(result["maximum_absolute_energy_error"] for result in results),
        "all_cases_passed": all(result["passed"] for result in results),
        "cases": results,
    }
    serialization_payload = {
        "task_id": "TM-IR-001",
        "run_id": RUN_ID,
        "examples": serialization_examples,
    }
    source_rows = [
        {
            "path": relative_path,
            "bytes": (REPO_ROOT / relative_path).stat().st_size,
            "sha256": _sha256(REPO_ROOT / relative_path),
        }
        for relative_path in SOURCE_PATHS
    ]
    source_payload = {
        "task_id": "TM-IR-001",
        "run_id": RUN_ID,
        "algorithm": "SHA-256",
        "aggregate_sha256": hashlib.sha256(_json_bytes(source_rows)).hexdigest(),
        "files": source_rows,
    }

    files = {
        "generation-config.json": configuration,
        "environment.json": environment,
        "projection-fixtures.json": projection_payload,
        "oracle-results.json": result_payload,
        "serialization-fixture.json": serialization_payload,
        "source-files.json": source_payload,
    }
    for filename, value in files.items():
        _write_json(output / filename, value)
    manifest = {
        "task_id": "TM-IR-001",
        "run_id": RUN_ID,
        "algorithm": "SHA-256",
        "files": [
            {
                "path": filename,
                "bytes": (output / filename).stat().st_size,
                "sha256": _sha256(output / filename),
            }
            for filename in sorted(files)
        ],
    }
    _write_json(output / "manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args()
    output = arguments.out if arguments.out.is_absolute() else REPO_ROOT / arguments.out
    generate(output.resolve(), overwrite=arguments.overwrite)


if __name__ == "__main__":
    main()
