"""JSON evaluator for Gibbsiq golden fixtures.

Compares a candidate JSON document against exact/diagnostic fixtures under
``reference/08-evaluation/fixtures``; writes a JSON report.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gibbsiq.benchmark_oracle import (
    DEFAULT_TOLERANCE,
    close_within,
    validate_tolerance,
    verify_benchmark_fixture,
)


UNORDERED_LIST_KEYS = {
    "energy_table",
    "best_binary_samples",
    "best_spin_samples",
    "required_flags",
    "sample_counts",
}

# Row aliases for list-shaped candidates (normalize_candidate forms 1/2), priority order.
_ROW_ID_KEYS = ("id", "fixture_id")
_ROW_ACTUAL_KEYS = ("actual", "output", "result")
# Ignored top-level keys for flat id -> output map candidates.
_CANDIDATE_METADATA_KEYS = frozenset({"schema_version", "metadata", "generated_by", "created_at"})


@dataclass(frozen=True, slots=True)
class Difference:
    path: str
    code: str
    message: str
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "path": self.path,
            "code": self.code,
            "message": self.message,
        }
        if self.expected is not None:
            data["expected"] = self.expected
        if self.actual is not None:
            data["actual"] = self.actual
        return data


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_fixture_dir() -> Path:
    return repository_root() / "reference" / "08-evaluation" / "fixtures"


def default_benchmark_fixture() -> Path:
    return repository_root() / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_fixture_sets(fixture_dir: Path, benchmark_path: Path | None = None) -> dict[str, Any]:
    exact = load_json(fixture_dir / "exact-small-instances.json")
    diagnostics = load_json(fixture_dir / "diagnostic-fixtures.json")

    if benchmark_path is None:
        benchmark_path = default_benchmark_fixture()
    benchmark = load_json(benchmark_path) if benchmark_path.exists() else {"fixtures": []}

    fixtures: dict[str, dict[str, Any]] = {}
    groups: dict[str, list[str]] = {"exact": [], "diagnostic": [], "benchmark": []}

    for group_name, payload in (
        ("exact", exact),
        ("diagnostic", diagnostics),
        ("benchmark", benchmark),
    ):
        for fixture in payload["fixtures"]:
            fixture_id = fixture["id"]
            if fixture_id in fixtures:
                raise ValueError(f"duplicate fixture id: {fixture_id}")
            fixtures[fixture_id] = fixture
            groups[group_name].append(fixture_id)

    return {
        "schema_version": {
            "exact": exact.get("schema_version"),
            "diagnostic": diagnostics.get("schema_version"),
            "benchmark": benchmark.get("schema_version"),
        },
        "fixtures": fixtures,
        "groups": groups,
    }


def _extract_row(index: int, row: Any) -> tuple[str, Any]:
    """Extract ``(fixture_id, actual)`` from a list-shaped candidate row.

    id: first truthy match in ``_ROW_ID_KEYS``. actual: first present key in
    ``_ROW_ACTUAL_KEYS``, else row minus its id keys.
    """
    if not isinstance(row, dict):
        raise ValueError(f"candidate row {index} must be an object")
    fixture_id = next((row[key] for key in _ROW_ID_KEYS if row.get(key)), None)
    if not isinstance(fixture_id, str) or not fixture_id:
        raise ValueError(f"candidate row {index} is missing id/fixture_id")
    actual = next((row[key] for key in _ROW_ACTUAL_KEYS if key in row), None)
    if actual is None:
        actual = {key: value for key, value in row.items() if key not in _ROW_ID_KEYS}
    return fixture_id, actual


def normalize_candidate(candidate: Any) -> dict[str, Any]:
    """Map fixture id to actual output. Accepted forms:

    1. ``{"results": [{"id": "fixture_id", "actual": {...}}]}``
    2. ``{"fixtures": [{"id": "fixture_id", "actual": {...}}]}``
    3. ``{"fixture_id": {...}, "another_fixture": {...}}``

    List forms: id from ``_ROW_ID_KEYS``, payload from ``_ROW_ACTUAL_KEYS``.
    Form 3: ``_CANDIDATE_METADATA_KEYS`` ignored.
    """
    if not isinstance(candidate, dict):
        raise ValueError("candidate JSON must be an object")

    rows = candidate.get("results", candidate.get("fixtures"))
    if isinstance(rows, list):
        normalized: dict[str, Any] = {}
        for index, row in enumerate(rows):
            fixture_id, actual = _extract_row(index, row)
            if fixture_id in normalized:
                raise ValueError(f"candidate row {index} duplicates fixture id {fixture_id!r}")
            normalized[fixture_id] = actual
        return normalized

    return {key: value for key, value in candidate.items() if key not in _CANDIDATE_METADATA_KEYS}


def _mismatch(
    path: str, expected: Any, actual: Any, message: str = "value does not match"
) -> list[Difference]:
    return [
        Difference(
            path=path,
            code="value_mismatch",
            message=message,
            expected=expected,
            actual=actual,
        )
    ]


def compare_values(
    expected: Any, actual: Any, path: str, tolerance: float, *, key: str | None = None
) -> list[Difference]:
    """Deep-compare ``actual`` against ``expected``.

    ``key`` is the enclosing mapping key (None at root / list elements);
    selects multiset vs ordered list comparison via ``UNORDERED_LIST_KEYS``.
    """
    if isinstance(expected, bool):
        return [] if isinstance(actual, bool) and expected == actual else _mismatch(path, expected, actual)

    if expected is None or isinstance(expected, str):
        return [] if expected == actual else _mismatch(path, expected, actual)

    if isinstance(expected, int):
        if not isinstance(actual, bool) and expected == actual:
            return []
        return _mismatch(path, expected, actual, "integer value does not match")

    if isinstance(expected, float):
        if close_within(actual, expected, tolerance):
            return []
        return [
            Difference(
                path=path,
                code="float_mismatch",
                message=f"float value differs by more than {tolerance}",
                expected=expected,
                actual=actual,
            )
        ]

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [
                Difference(
                    path=path,
                    code="type_mismatch",
                    message="expected an object",
                    expected="object",
                    actual=type(actual).__name__,
                )
            ]
        differences: list[Difference] = []
        for child_key, expected_value in expected.items():
            child_path = f"{path}.{child_key}" if path else child_key
            if child_key not in actual:
                differences.append(
                    Difference(
                        path=child_path,
                        code="missing_key",
                        message="required key is missing",
                        expected=expected_value,
                    )
                )
                continue
            differences.extend(
                compare_values(expected_value, actual[child_key], child_path, tolerance, key=child_key)
            )
        return differences

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [
                Difference(
                    path=path,
                    code="type_mismatch",
                    message="expected a list",
                    expected="list",
                    actual=type(actual).__name__,
                )
            ]
        if key in UNORDERED_LIST_KEYS:
            return compare_unordered_lists(expected, actual, path, tolerance)
        return compare_ordered_lists(expected, actual, path, tolerance)

    return [] if expected == actual else _mismatch(path, expected, actual)


def compare_ordered_lists(
    expected: list[Any], actual: list[Any], path: str, tolerance: float
) -> list[Difference]:
    differences: list[Difference] = []
    if len(expected) != len(actual):
        differences.append(
            Difference(
                path=path,
                code="length_mismatch",
                message="list length does not match",
                expected=len(expected),
                actual=len(actual),
            )
        )
    for index, expected_value in enumerate(expected[: len(actual)]):
        differences.extend(compare_values(expected_value, actual[index], f"{path}[{index}]", tolerance))
    return differences


def compare_unordered_lists(
    expected: list[Any],
    actual: list[Any],
    path: str,
    tolerance: float,
) -> list[Difference]:
    """Compare as an unordered multiset, preserving float tolerance.

    Bipartite maximum matching, not greedy pairing — tolerance neighborhoods
    can overlap. Multiplicity preserved; one actual item per expected item.
    """
    if len(expected) == len(actual):
        compatible = [
            [
                not compare_values(expected_item, actual_item, f"{path}[*]", tolerance)
                for actual_item in actual
            ]
            for expected_item in expected
        ]
        matched_expected = [-1] * len(actual)

        def augment(expected_index: int, seen_actual: set[int]) -> bool:
            for actual_index, is_compatible in enumerate(compatible[expected_index]):
                if not is_compatible or actual_index in seen_actual:
                    continue
                seen_actual.add(actual_index)
                previous = matched_expected[actual_index]
                if previous == -1 or augment(previous, seen_actual):
                    matched_expected[actual_index] = expected_index
                    return True
            return False

        if all(augment(index, set()) for index in range(len(expected))):
            return []

    if expected == actual:
        return []
    return [
        Difference(
            path=path,
            code="unordered_list_mismatch",
            message="list items do not match as an unordered multiset",
            expected=expected,
            actual=actual,
        )
    ]


def evaluate_candidate(
    candidate: dict[str, Any],
    fixture_dir: Path | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict[str, Any]:
    tolerance = validate_tolerance(tolerance)
    fixture_dir = fixture_dir or default_fixture_dir()
    fixture_sets = load_fixture_sets(fixture_dir)
    fixtures: dict[str, dict[str, Any]] = fixture_sets["fixtures"]
    benchmark_ids = set(fixture_sets["groups"].get("benchmark", []))
    actual_by_id = normalize_candidate(candidate)

    results = []
    passed = 0
    failed = 0
    missing = 0

    for fixture_id, fixture in fixtures.items():
        if fixture_id not in actual_by_id:
            missing += 1
            results.append(
                {
                    "id": fixture_id,
                    "status": "missing",
                    "passed": False,
                    "differences": [
                        {
                            "path": fixture_id,
                            "code": "missing_fixture_result",
                            "message": "candidate did not include output for this fixture",
                        }
                    ],
                }
            )
            continue

        actual = actual_by_id[fixture_id]
        if fixture_id in benchmark_ids:
            difference_dicts = verify_benchmark_fixture(fixture, actual, tolerance)
        else:
            differences = compare_values(fixture["expected"], actual, fixture_id, tolerance)
            difference_dicts = [difference.to_dict() for difference in differences]
        status = "passed" if not difference_dicts else "failed"
        passed += int(status == "passed")
        failed += int(status == "failed")
        results.append(
            {
                "id": fixture_id,
                "status": status,
                "passed": status == "passed",
                "difference_count": len(difference_dicts),
                "differences": difference_dicts,
            }
        )

    unknown_ids = sorted(set(actual_by_id) - set(fixtures))
    overall_passed = failed == 0 and missing == 0 and not unknown_ids
    return {
        "schema_version": "2026-05-28",
        "passed": overall_passed,
        "summary": {
            "total_fixtures": len(fixtures),
            "passed": passed,
            "failed": failed,
            "missing": missing,
            "unknown": len(unknown_ids),
            "tolerance": tolerance,
        },
        "fixture_schema_version": fixture_sets["schema_version"],
        "results": results,
        "unknown_fixture_ids": unknown_ids,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate candidate Gibbsiq fixture outputs and print a JSON report."
    )
    parser.add_argument("candidate", type=Path, help="Path to candidate JSON output.")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=default_fixture_dir(),
        help="Fixture directory. Defaults to reference/08-evaluation/fixtures.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help="Absolute tolerance for floating-point comparisons.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the JSON report. stdout is always used when omitted.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate = load_json(args.candidate)
    report = evaluate_candidate(candidate, fixture_dir=args.fixtures, tolerance=args.tolerance)
    text = json.dumps(report, indent=2, sort_keys=True)

    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
