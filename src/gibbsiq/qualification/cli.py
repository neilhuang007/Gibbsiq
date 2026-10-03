"""Offline qualification and evidence inspection commands."""

from __future__ import annotations

import argparse
from importlib import util
from pathlib import Path
import sys
from typing import Any, Sequence, cast

from gibbsiq import __version__
from gibbsiq.qualification.adapters.spin import SpinConditionalBackend
from gibbsiq.qualification.artifacts import inspect_bundle, plan_from_dict, record_to_dict
from gibbsiq.qualification.comparison import compare_bundles
from gibbsiq.qualification.contracts import RunPlan, canonical_json, parse_json
from gibbsiq.qualification.doctor import doctor_report
from gibbsiq.qualification.engine import UnsupportedCapabilityError
from gibbsiq.qualification.examples import SPIN_CANDIDATES, spin_conditional_plan
from gibbsiq.qualification.reporting import render_comparison, render_report
from gibbsiq.qualification.workflow import qualify


_STATUS_EXIT_CODES = {
    "pass": 0,
    "qualified": 0,
    "no_regression_under_contract": 0,
    "fail": 1,
    "failed_validation": 1,
    "regression": 1,
    "invalid": 2,
    "inconclusive": 3,
    "no_feasible_policy": 3,
    "inconclusive_validation": 3,
    "budget_exhausted": 3,
    "unsupported": 4,
    "error": 5,
    "cancelled": 130,
}
_TINY_Z1T_MODULES = ("jax", "equinox", "numpy", "z1t")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gibbsiq", description="Offline stochastic qualification")
    parser.add_argument("--version", action="version", version=f"gibbsiq {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    qualification = commands.add_parser("qualify", help="execute a frozen qualification plan")
    source = qualification.add_mutually_exclusive_group(required=True)
    source.add_argument("--example", choices=("spin-conditional", "tiny-z1t", "torx-two-gate"))
    source.add_argument("--spec", type=Path, help="frozen schema-1 RunPlan JSON")
    qualification.add_argument("--output", type=Path, required=True)
    qualification.add_argument("--runs", type=int)
    qualification.add_argument("--samples", type=int)
    qualification.add_argument("--seed", type=int)
    qualification.add_argument("--candidate", choices=tuple(SPIN_CANDIDATES))
    qualification.add_argument("--resume", action="store_true")
    qualification.add_argument("--json", action="store_true")
    inspection = commands.add_parser("inspect", help="inspect stored evidence without running a backend")
    inspection.add_argument("path", type=Path)
    inspection.add_argument(
        "--verify", action="store_true", help="require optional array structural validation"
    )
    inspection.add_argument("--json", action="store_true")
    comparison = commands.add_parser("compare", help="compare two verified evidence bundles")
    comparison.add_argument("baseline", type=Path)
    comparison.add_argument("candidate", type=Path)
    comparison.add_argument("--candidate-change")
    comparison.add_argument("--json", action="store_true")
    tuning = commands.add_parser("tune", help="run a bounded built-in policy search")
    tuning.add_argument("--example", required=True, choices=("tiny-z1t", "no-feasible-policy"))
    tuning.add_argument("--output", type=Path, required=True)
    tuning.add_argument("--json", action="store_true")
    doctor = commands.add_parser("doctor", help="show static local qualification capabilities")
    doctor.add_argument("--json", action="store_true")
    return parser


def _read_plan(path: Path) -> RunPlan:
    with path.open("rb") as stream:
        payload = stream.read(1024 * 1024 + 1)
    if len(payload) > 1024 * 1024:
        raise ValueError("frozen plan JSON exceeds 1 MiB")
    return plan_from_dict(parse_json(payload.decode("utf-8")))


def _require_tiny_z1t_stack() -> None:
    missing = [name for name in _TINY_Z1T_MODULES if util.find_spec(name) is None]
    if missing:
        raise UnsupportedCapabilityError(
            "tiny Z1T requires the pinned optional modules: " + ", ".join(missing)
        )


def _builtin_backends(plan: RunPlan) -> dict[str, object]:
    identity = plan.workload.candidate.identity
    for profile, candidate_id in SPIN_CANDIDATES.items():
        if identity == candidate_id:
            return {candidate_id: SpinConditionalBackend(profile)}
    if plan.workload.workload_id == "torx-two-gate-v1":
        from gibbsiq.qualification.adapters.torx import TorxCircuitBackend

        return {identity: TorxCircuitBackend.from_plan(plan)}
    if plan.workload.workload_id == "tiny-z1t-teacher-forced-v1":
        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend

        backend = TinyModelBackend.from_plan(plan)
        _require_tiny_z1t_stack()
        return {identity: backend}
    return {}


def _example_plan(name: str, recipe: dict[str, object]) -> tuple[RunPlan, dict[str, object]]:
    runs = cast(int | None, recipe.get("runs"))
    samples = cast(int | None, recipe.get("samples"))
    seed = cast(int | None, recipe.get("seed"))
    if name == "spin-conditional":
        plan = spin_conditional_plan(
            **{key: value for key, value in recipe.items() if value is not None}  # type: ignore[arg-type]
        )
        return plan, _builtin_backends(plan)
    if "candidate" in recipe:
        raise ValueError("--candidate is supported only for spin-conditional")
    if name == "torx-two-gate":
        from gibbsiq.qualification.adapters.torx import TorxCircuitBackend

        torx_backend = TorxCircuitBackend()
        plan = torx_backend.plan(
            **{
                key: value
                for key, value in {"runs": runs, "samples": samples, "seed": seed}.items()
                if value is not None
            }
        )  # type: ignore[arg-type]
        return plan, {plan.workload.candidate.identity: torx_backend}
    from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
    from gibbsiq.qualification.model_evaluation import tiny_split_manifest

    _require_tiny_z1t_stack()
    model_backend = TinyModelBackend(tiny_split_manifest().evaluation)
    plan = model_backend.plan(
        runs=16 if runs is None else runs,
        samples=32 if samples is None else samples,
        seed=20260923 if seed is None else seed,
    )
    return plan, {plan.workload.candidate.identity: model_backend}


def _exit_for_report(qualification: str, execution: str) -> int:
    if execution == "cancelled":
        return 130
    if qualification == "unsupported":
        return 4
    if qualification == "invalid":
        return 2
    if execution == "error":
        return 5
    return _STATUS_EXIT_CODES[qualification]


def _exit_for_comparison(outcome: object, compatible: object) -> int:
    if compatible is not True:
        return 2
    return _STATUS_EXIT_CODES.get(str(outcome), 5)


def _exit_for_search(lifecycle: object) -> int:
    return _STATUS_EXIT_CODES.get(str(lifecycle), 5)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            status_report = doctor_report()
            if args.json:
                print(canonical_json(status_report).decode("utf-8"))
            else:
                print(
                    f"gibbsiq {status_report['package']['version']}\nPython: {status_report['python']}\nPlatform: {status_report['platform']}"
                )
                for item in status_report["optional"]:
                    state = item["version"] or "not installed"
                    print(f"{item['distribution']}: {state}; module available={item['module_available']}")
            return 0
        if args.command == "compare":
            summary = compare_bundles(args.baseline, args.candidate, candidate_change=args.candidate_change)
            print(
                canonical_json(summary).decode("utf-8") if args.json else render_comparison(summary),
                end="\n" if args.json else "",
            )
            return _exit_for_comparison(summary["outcome"], summary["compatible"])
        if args.command == "tune":
            if args.example == "no-feasible-policy":
                from gibbsiq.qualification.adapters.analytic_search import tune_no_feasible_policy

                search = tune_no_feasible_policy(destination=args.output)
            else:
                from gibbsiq.qualification.adapters.model_search import tune_tiny_model

                search = tune_tiny_model(destination=args.output)
            payload: dict[str, Any] = search
            if args.json:
                print(canonical_json(payload).decode("utf-8"))
            else:
                from gibbsiq.qualification.policy_search import render_search_summary

                print(render_search_summary(payload), end="")
            return _exit_for_search(payload.get("lifecycle"))
        if args.command == "qualify":
            recipe = {
                name: value
                for name in ("runs", "samples", "seed", "candidate")
                if (value := getattr(args, name)) is not None
            }
            if args.spec is not None:
                if recipe:
                    raise ValueError("example recipe options cannot be used with --spec")
                plan = _read_plan(args.spec)
                backends = _builtin_backends(plan)
            else:
                plan, backends = _example_plan(args.example, recipe)
            report = qualify(plan, backends=backends, destination=args.output, resume=args.resume)
            if args.json:
                print(
                    canonical_json({"report": record_to_dict(report), "output": str(args.output)}).decode(
                        "utf-8"
                    )
                )
            else:
                print(
                    render_report(
                        plan, execution=report.execution, qualification=report.qualification, report=report
                    ),
                    end="",
                )
            return _exit_for_report(report.qualification, report.execution)
        snapshot = inspect_bundle(args.path, verify=args.verify)
        if args.json:
            print(
                canonical_json(
                    {
                        "execution": snapshot.execution,
                        "qualification": snapshot.qualification,
                        "payload_validation": snapshot.payload_validation,
                        "reason": snapshot.reason,
                        "report": None if snapshot.report is None else record_to_dict(snapshot.report),
                    }
                ).decode("utf-8")
            )
        else:
            scientific_qualification = (
                snapshot.report.qualification if snapshot.report is not None else snapshot.qualification
            )
            print(
                render_report(
                    snapshot.plan,
                    execution=snapshot.execution,
                    qualification=scientific_qualification,
                    report=snapshot.report,
                ),
                end="",
            )
            print(f"Payload validation: {snapshot.payload_validation}")
            if snapshot.reason:
                print(f"Inspection reason: {snapshot.reason}")
        return 4 if args.verify and snapshot.payload_validation == "unavailable" else 0
    except KeyboardInterrupt:
        return 130
    except (ImportError, ModuleNotFoundError) as error:
        print(f"gibbsiq: optional qualification backend unavailable: {error}", file=sys.stderr)
        return 4
    except UnsupportedCapabilityError as error:
        print(f"gibbsiq: unsupported qualification capability: {error}", file=sys.stderr)
        return 4
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        print(f"gibbsiq: {error}", file=sys.stderr)
        return 2


__all__ = ["main"]
