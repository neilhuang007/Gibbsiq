"""Exercise the dependency-free Gibbsiq wheel from outside its checkout."""

from __future__ import annotations

import importlib.abc
import importlib.metadata
import importlib.resources
import json
import math
import os
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import Any


OPTIONAL_ROOTS = frozenset(
    {
        "arviz",
        "dimod",
        "equinox",
        "jax",
        "networkx",
        "numpy",
        "thrml",
        "torx",
        "z1t",
    }
)


class _RejectOptionalDependencies(importlib.abc.MetaPathFinder):
    """Make an accidental optional import fail even if the dependency is installed."""

    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> None:
        root = fullname.partition(".")[0]
        if root in OPTIONAL_ROOTS:
            raise RuntimeError(f"installed-core smoke forbids optional dependency {root!r}")
        return None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _require_close(actual: float, expected: float, *, name: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-14):
        raise RuntimeError(f"{name}: expected {expected!r}, received {actual!r}")


def _command_context(result: subprocess.CompletedProcess[str]) -> str:
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    return f"exit={result.returncode}, stdout={stdout!r}, stderr={stderr!r}"


def _run_cli(
    command: list[str], *, cwd: Path, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"installed console command timed out after 30 seconds: {command!r}") from error


def _read_report(path: Path, *, context: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{context}: could not read JSON report at {path}") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"{context}: report must be a JSON object")
    return payload


def _run_fixture_case(
    candidate: dict[str, dict[str, Any]],
    *,
    case_name: str,
    expected_returncode: int,
    executable: Path,
    workdir: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    candidate_path = workdir / f"{case_name}-candidate.json"
    report_path = workdir / f"{case_name}-report.json"
    candidate_path.write_text(
        json.dumps(candidate, separators=(",", ":")),
        encoding="utf-8",
    )
    result = _run_cli(
        [str(executable), str(candidate_path), "--output", str(report_path)],
        cwd=workdir,
        environment=environment,
    )
    _require(
        result.returncode == expected_returncode,
        f"installed console {case_name} fixture run had wrong exit: "
        f"expected {expected_returncode}, {_command_context(result)}",
    )
    return _read_report(report_path, context=f"{case_name} fixture run")


def _independent_max_cut(fixture: dict[str, Any], *, fixture_id: str) -> int:
    try:
        variables = fixture["input"]["variables"]
        edges = fixture["input"]["edges"]
        expected_variables = {
            "maxcut_triangle_unweighted": 3,
            "maxcut_cycle4_unweighted": 4,
        }[fixture_id]
        _require(
            len(variables) == expected_variables,
            f"{fixture_id}: expected {expected_variables} variables, received {len(variables)}",
        )
        positions = {variable: index for index, variable in enumerate(variables)}
        _require(len(positions) == len(variables), f"{fixture_id}: variables must be unique")
        best = 0
        for assignment in range(1 << len(variables)):
            cut = sum(
                ((assignment >> positions[left]) & 1) != ((assignment >> positions[right]) & 1)
                for left, right in edges
            )
            best = max(best, cut)
        return best
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"{fixture_id}: malformed Max-Cut fixture") from error


def _check_core() -> dict[str, Any]:
    sys.meta_path.insert(0, _RejectOptionalDependencies())

    import gibbsiq
    from gibbsiq.qualification.adapters.reference import spin_conditional
    from gibbsiq.qualification.adapters.z1t import TinyZ1TConfig
    from gibbsiq.qualification.adapters.model_preflight import (
        Z1TShape,
        estimate_z1t_array_bytes,
        preflight_checkpoint,
    )
    from gibbsiq.qualification.contracts import Acceptance, Bounds, MetricSpec
    from gibbsiq.qualification.statistics import evaluate_metric, required_units

    package_file = Path(gibbsiq.__file__).resolve(strict=True)
    distribution = importlib.metadata.distribution("gibbsiq")
    metadata = distribution.metadata
    _require(
        importlib.metadata.version("gibbsiq") == gibbsiq.__version__,
        "installed distribution and runtime versions disagree",
    )
    requirements = metadata.get_all("Requires-Dist") or []
    _require(
        all("extra ==" in requirement for requirement in requirements),
        f"core wheel unexpectedly declares an unconditional dependency: {requirements!r}",
    )
    _require(
        metadata.get("License-Expression") == "MIT AND Apache-2.0",
        "installed distribution lost its SPDX license expression",
    )
    license_entries = metadata.get_all("License-File") or []
    _require(
        {Path(entry).name for entry in license_entries} >= {"LICENSE", "Z1T_LICENSE.txt"},
        f"installed metadata has incomplete license files: {license_entries!r}",
    )
    installed_files = tuple(distribution.files or ())
    license_files = {
        Path(str(item)).name: Path(distribution.locate_file(item)).resolve(strict=True)
        for item in installed_files
        if Path(str(item)).name in {"LICENSE", "Z1T_LICENSE.txt"}
    }
    _require(set(license_files) == {"LICENSE", "Z1T_LICENSE.txt"}, "wheel license files are missing")
    _require(
        "MIT License" in license_files["LICENSE"].read_text(encoding="utf-8"), "MIT license is unreadable"
    )
    _require(
        "Apache License" in license_files["Z1T_LICENSE.txt"].read_text(encoding="utf-8"),
        "wheel Apache notice is unreadable",
    )
    quickstart = importlib.resources.files("gibbsiq").joinpath("data/qualification/QUICKSTART.md")
    quickstart_text = quickstart.read_text(encoding="utf-8")
    _require(bool(quickstart_text.strip()), "installed QUICKSTART is empty")
    purelib = Path(sysconfig.get_path("purelib")).resolve(strict=True)
    try:
        package_file.relative_to(purelib)
    except ValueError as error:
        raise RuntimeError(
            f"gibbsiq was imported from the checkout instead of the installed purelib: "
            f"module={package_file}, purelib={purelib}"
        ) from error

    imported_optional = sorted(OPTIONAL_ROOTS.intersection(sys.modules))
    _require(
        not imported_optional,
        f"plain installed-core import loaded optional dependencies: {imported_optional!r}",
    )

    moments = spin_conditional(math.log(3.0) / 2.0, samples=10)
    for name, expected in (
        ("probability_up", 0.75),
        ("mean", 0.5),
        ("variance", 0.75),
        ("mean_variance", 0.075),
    ):
        _require_close(getattr(moments, name), expected, name=f"spin_conditional.{name}")

    bounds = Bounds(0.0, 1.0)
    planned_units = required_units(bounds, alpha=0.05, half_width=0.05)
    _require(planned_units == 738, f"required_units: expected 738, received {planned_units}")
    spec = MetricSpec(
        metric_id="installed-bounded-smoke",
        units="fraction",
        direction="smaller_is_better",
        comparison="candidate error rate",
        acceptance=Acceptance(kind="upper", upper=0.1),
        evidence_mode="bounded_fixed_n",
        planned_units=planned_units,
        replication_unit="independent_run",
        scope="fixed_inputs",
        bounds=bounds,
    )
    complete_zero = evaluate_metric(spec, [0.0] * planned_units, alpha=0.05)
    complete_one = evaluate_metric(spec, [1.0] * planned_units, alpha=0.05)
    single_zero = evaluate_metric(spec, [0.0], alpha=0.05)
    empty = evaluate_metric(spec, [], alpha=0.05)
    _require(complete_zero.outcome == "pass", "complete all-zero bounded metric did not pass")
    _require(complete_one.outcome == "fail", "complete all-one bounded metric did not fail")
    _require(single_zero.outcome == "inconclusive", "single-unit bounded metric was not inconclusive")
    _require(empty.availability == "unavailable", "empty bounded metric was not unavailable")
    _require(TinyZ1TConfig().n_embed == 8, "tiny model config is unavailable in a core install")
    _require(estimate_z1t_array_bytes(Z1TShape()) == 3388, "installed model resource estimate changed")
    preflight = preflight_checkpoint(memory_bytes=0, disk_bytes=0)
    _require(not preflight.ready, "undeclared checkpoint prerequisites were accepted")
    license_path = package_file.parent / "qualification/adapters/Z1T_LICENSE.txt"
    _require("Apache License" in license_path.read_text(encoding="utf-8"), "in-package notice is missing")

    return {
        "package_path": str(package_file),
        "version": gibbsiq.__version__,
        "license_expression": metadata.get("License-Expression"),
        "license_files": sorted(license_files),
        "quickstart_bytes": len(quickstart_text.encode("utf-8")),
        "purelib": str(purelib),
        "optional_imports": imported_optional,
        "analytic_probability_up": moments.probability_up,
        "required_units": planned_units,
        "checkpoint_preflight_ready": preflight.ready,
        "bounded_outcomes": [
            complete_zero.outcome,
            complete_one.outcome,
            single_zero.outcome,
            empty.availability,
        ],
    }


def _check_legacy_console() -> dict[str, Any]:
    from gibbsiq.evaluation import load_fixture_sets

    scripts = Path(sysconfig.get_path("scripts"))
    executable = scripts / ("gibbsiq-evaluate.exe" if os.name == "nt" else "gibbsiq-evaluate")
    _require(executable.is_file(), f"installed console entry point is missing: {executable}")

    fixture_sets = load_fixture_sets()
    groups = {name: len(fixture_ids) for name, fixture_ids in fixture_sets["groups"].items()}
    expected_groups = {"exact": 5, "diagnostic": 7, "benchmark": 27}
    expected_fixture_count = sum(expected_groups.values())
    _require(groups == expected_groups, f"fixture group sizes: expected {expected_groups}, received {groups}")
    fixtures: dict[str, dict[str, Any]] = fixture_sets["fixtures"]

    independent_optima = {
        fixture_id: _independent_max_cut(fixtures[fixture_id], fixture_id=fixture_id)
        for fixture_id in ("maxcut_triangle_unweighted", "maxcut_cycle4_unweighted")
    }
    expected_optima = {"maxcut_triangle_unweighted": 2, "maxcut_cycle4_unweighted": 4}
    _require(
        independent_optima == expected_optima,
        f"independent Max-Cut optima: expected {expected_optima}, received {independent_optima}",
    )
    for fixture_id, optimum in expected_optima.items():
        bundled = fixtures[fixture_id]["expected"]["best_cut_value"]
        _require(
            bundled == optimum,
            f"{fixture_id}: bundled best_cut_value expected {optimum}, received {bundled!r}",
        )

    environment = {
        key: value for key, value in os.environ.items() if key.upper() not in {"PYTHONHOME", "PYTHONPATH"}
    }
    with tempfile.TemporaryDirectory(prefix="gibbsiq-installed-console-") as temporary_directory:
        workdir = Path(temporary_directory)
        help_result = _run_cli([str(executable), "--help"], cwd=workdir, environment=environment)
        _require(
            help_result.returncode == 0,
            f"installed console --help failed: {_command_context(help_result)}",
        )

        candidate = {fixture_id: fixture["expected"] for fixture_id, fixture in fixtures.items()}
        _require(
            len(candidate) == expected_fixture_count,
            f"expected {expected_fixture_count} candidate blocks, received {len(candidate)}",
        )
        positive_report = _run_fixture_case(
            candidate,
            case_name="positive",
            expected_returncode=0,
            executable=executable,
            workdir=workdir,
            environment=environment,
        )
        positive_summary = positive_report.get("summary")
        _require(positive_report.get("passed") is True, "positive fixture report did not pass")
        _require(
            isinstance(positive_summary, dict)
            and positive_summary.get("passed") == expected_fixture_count
            and positive_summary.get("failed") == 0,
            f"positive fixture summary was unexpected: {positive_summary!r}",
        )

        corrupt_candidate = candidate.copy()
        corrupt_candidate["maxcut_triangle_unweighted"] = candidate["maxcut_triangle_unweighted"].copy()
        corrupt_candidate["maxcut_triangle_unweighted"]["best_cut_value"] = 3
        negative_report = _run_fixture_case(
            corrupt_candidate,
            case_name="negative",
            expected_returncode=1,
            executable=executable,
            workdir=workdir,
            environment=environment,
        )
        negative_summary = negative_report.get("summary")
        _require(negative_report.get("passed") is False, "negative fixture report unexpectedly passed")
        _require(
            isinstance(negative_summary, dict) and negative_summary.get("failed") == 1,
            f"negative fixture summary was unexpected: {negative_summary!r}",
        )

    return {
        "executable": str(executable),
        "fixture_groups": groups,
        "independent_max_cut": independent_optima,
        "positive": positive_summary,
        "negative": negative_summary,
    }


def _check_qualification_console() -> dict[str, Any]:
    scripts = Path(sysconfig.get_path("scripts"))
    executable = scripts / ("gibbsiq.exe" if os.name == "nt" else "gibbsiq")
    _require(executable.is_file(), f"installed qualification entry point is missing: {executable}")
    environment = {
        key: value for key, value in os.environ.items() if key.upper() not in {"PYTHONHOME", "PYTHONPATH"}
    }
    cases = (("iid", 1024, "pass", 0), ("sign-reversed", 256, "fail", 1), ("iid", 16, "inconclusive", 3))
    outcomes = []
    with tempfile.TemporaryDirectory(prefix="gibbsiq-installed-qualification-") as temporary:
        workdir = Path(temporary)
        for candidate, runs, expected, code in cases:
            destination = workdir / expected
            result = _run_cli(
                [
                    str(executable),
                    "qualify",
                    "--example",
                    "spin-conditional",
                    "--candidate",
                    candidate,
                    "--runs",
                    str(runs),
                    "--output",
                    str(destination),
                    "--json",
                ],
                cwd=workdir,
                environment=environment,
            )
            _require(result.returncode == code, f"{expected} qualification: {_command_context(result)}")
            report = json.loads(result.stdout)["report"]
            _require(report["qualification"] == expected, f"unexpected {expected} report decision")
            metric = report["metrics"][0]
            _require(metric["observed_units"] == runs, "qualification omitted planned observations")
            observations = [
                json.loads(line)["record"]["observations"][0]["values"][0]
                for line in (destination / "runs.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            _require(len(observations) == runs, "journal does not contain each independent run")
            _require_close(
                metric["estimate"], math.fsum(observations) / runs - 0.5, name="persisted mean difference"
            )
            interval = metric["interval"]
            if expected == "pass":
                _require(
                    -0.125 < interval["lower"] < interval["upper"] < 0.125,
                    "passing interval is outside margin",
                )
            elif expected == "fail":
                _require(interval["upper"] < -0.125, "sign reversal was not detected numerically")
            else:
                _require(interval["lower"] < -0.125 < interval["upper"], "short run lost its uncertainty")
            inspected = _run_cli(
                [str(executable), "inspect", str(destination), "--verify", "--json"],
                cwd=workdir,
                environment=environment,
            )
            _require(inspected.returncode == 0, f"installed inspection failed: {_command_context(inspected)}")
            _require(json.loads(inspected.stdout)["report"] == report, "inspection changed a stored decision")
            outcomes.append(
                {"qualification": expected, "observed_units": runs, "estimate": metric["estimate"]}
            )

        comparison = _run_cli(
            [
                str(executable),
                "compare",
                str(workdir / "pass"),
                str(workdir / "fail"),
                "--candidate-change",
                "spin-conditional-sign-reversed-v1",
                "--json",
            ],
            cwd=workdir,
            environment=environment,
        )
        _require(comparison.returncode == 1, f"regression gate: {_command_context(comparison)}")
        compared = json.loads(comparison.stdout)
        _require(compared["compatible"] and compared["outcome"] == "regression", "lost declared regression")
        _require(compared["metrics"][0]["delta"] < -0.5, "sign error did not change observed mean")
        _require(
            compared["metrics"][0]["difference_interval"]["upper"] < -0.5,
            "regression uncertainty does not resolve the planted defect",
        )
        search = _run_cli(
            [
                str(executable),
                "tune",
                "--example",
                "no-feasible-policy",
                "--output",
                str(workdir / "search"),
                "--json",
            ],
            cwd=workdir,
            environment=environment,
        )
        _require(search.returncode == 3, f"negative policy search: {_command_context(search)}")
        searched = json.loads(search.stdout)
        _require(
            searched["lifecycle"] == "no_feasible_policy" and searched["policy"] is None,
            "negative search exported a successful policy",
        )
        _require(len(searched["attempts"]) == 3, "negative search did not preserve all candidates")
        for attempt in searched["attempts"]:
            _require_close(attempt["quality_mean"], 2 * math.tanh(0.25), name="analytic sign error")
        doctor = _run_cli([str(executable), "doctor", "--json"], cwd=workdir, environment=environment)
        _require(doctor.returncode == 0, f"offline doctor: {_command_context(doctor)}")
        _require(json.loads(doctor.stdout)["package"]["name"] == "gibbsiq", "wrong installed doctor target")

        journal = workdir / "pass" / "runs.jsonl"
        journal.write_bytes(journal.read_bytes()[:-7])
        corrupt = _run_cli(
            [str(executable), "inspect", str(workdir / "pass"), "--verify"],
            cwd=workdir,
            environment=environment,
        )
        _require(corrupt.returncode == 2, "installed inspection accepted a truncated observation journal")
    return {"executable": str(executable), "outcomes": outcomes, "truncated_journal_rejected": True}


def main() -> int:
    result = {
        "status": "passed",
        "core": _check_core(),
        "legacy_console": _check_legacy_console(),
        "qualification_console": _check_qualification_console(),
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
