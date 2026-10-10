"""Rehearse containment and correction locally; no registry client or network access."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

from gibbsiq.qualification.adapters.spin import SpinConditionalBackend
from gibbsiq.qualification.artifacts import record_to_dict
from gibbsiq.qualification.contracts import canonical_json
from gibbsiq.qualification.examples import SPIN_CANDIDATES, spin_conditional_plan
from gibbsiq.qualification.workflow import qualify


class LocalReleaseHistory:
    """Small procedure fixture for numeric release versions, not a package resolver."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    @property
    def records(self) -> list[dict[str, Any]]:
        return deepcopy(self._records)

    def add(self, version: tuple[int, int, int], filename: str, qualification: str) -> None:
        if len(version) != 3 or any(type(part) is not int or part < 0 for part in version):
            raise ValueError("rehearsal versions must have three nonnegative integer parts")
        if not filename or Path(filename).name != filename:
            raise ValueError("filename must be a basename")
        if any(record["filename"] == filename for record in self._records):
            raise ValueError("a historical filename cannot be reused, including after removal")
        if any(record["version"] == list(version) for record in self._records):
            raise ValueError("use a new version for a correction")
        if qualification not in {"pass", "fail", "inconclusive", "invalid", "unsupported"}:
            raise ValueError("unknown qualification state")
        self._records.append(
            {
                "version": list(version),
                "filename": filename,
                "qualification": qualification,
                "warning": None,
                "removed": False,
            }
        )

    def yank(self, version: tuple[int, int, int], reason: str) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("yanking requires an explanation")
        for record in self._records:
            if record["version"] == list(version):
                record["warning"] = reason
                return
        raise LookupError("unknown version")

    def remove(self, filename: str) -> None:
        for record in self._records:
            if record["filename"] == filename:
                record["removed"] = True
                return
        raise LookupError("unknown filename")

    def resolve(self, *, exact: tuple[int, int, int] | None = None) -> dict[str, Any]:
        eligible = [
            record
            for record in self._records
            if not record["removed"]
            and (record["version"] == list(exact) if exact is not None else record["warning"] is None)
        ]
        if not eligible:
            raise LookupError("no eligible release")
        return deepcopy(max(eligible, key=lambda record: record["version"]))


def rehearse(destination: Path) -> dict[str, Any]:
    """Detect a real sign defect, retain its evidence, then qualify a correction."""
    destination.mkdir(parents=True, exist_ok=False)
    history = LocalReleaseHistory()
    reports = []
    for version, candidate, runs in (((0, 2, 0), "sign-reversed", 256), ((0, 2, 1), "iid", 1024)):
        name = "gibbsiq-" + ".".join(map(str, version)) + "-rehearsal-plan.json"
        plan = spin_conditional_plan(candidate=candidate, runs=runs)
        (destination / name).write_bytes(canonical_json(record_to_dict(plan)))
        report = qualify(
            plan,
            backends={SPIN_CANDIDATES[candidate]: SpinConditionalBackend(candidate)},
            destination=destination / candidate,
        )
        history.add(version, name, report.qualification)
        reports.append(record_to_dict(report))
        if candidate == "sign-reversed":
            if report.qualification != "fail" or report.metrics[0].estimate >= -0.5:
                raise RuntimeError("the planted behavioral defect was not detected")
            history.yank(version, "wrong conditional-mean sign; evidence retained in sign-reversed/")
        elif report.qualification != "pass":
            raise RuntimeError("the correction did not qualify")
    summary = {
        "schema": "local-release-rehearsal-v1",
        "records": history.records,
        "ordinary_selection": history.resolve(),
        "exact_bad_pin": history.resolve(exact=(0, 2, 0)),
        "reports": reports,
        "limitations": [
            "Local procedure fixture; no registry or installer was contacted.",
            "Artifact versions are rehearsal identifiers, not published versions.",
        ],
    }
    (destination / "recovery.json").write_bytes(canonical_json(summary))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = rehearse(args.output)
    print(canonical_json(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
