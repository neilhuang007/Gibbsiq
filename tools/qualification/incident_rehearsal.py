"""Rehearse containment and recovery from a corrupted qualification bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
from typing import Any, Iterable

from gibbsiq.qualification.artifacts import inspect_bundle, record_to_dict
from gibbsiq.qualification.contracts import canonical_json


MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_SECONDS = 90.0


def _tree_facts(root: Path, *, max_bytes: int = MAX_SOURCE_BYTES) -> tuple[int, str]:
    """Return bounded byte count and streaming tree hash in one filesystem pass."""
    digest = hashlib.sha256()
    total = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        size = path.stat().st_size
        total += size
        if total > max_bytes:
            raise ValueError("evidence scope exceeds the 32 MiB rehearsal limit")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return total, "sha256:" + digest.hexdigest()


def _outside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return True
    return False


def _corrupt_journal(bundle: Path) -> dict[str, str]:
    journal = bundle / "runs.jsonl"
    payload = bytearray(journal.read_bytes())
    marker = payload.find(b'"values":[')
    if marker < 0:
        raise RuntimeError("retained journal has no inline observation value to corrupt")
    position = marker + len(b'"values":[')
    while position < len(payload) and payload[position] not in b"-0123456789":
        position += 1
    if position >= len(payload):
        raise RuntimeError("retained journal value could not be located")
    original = chr(payload[position])
    payload[position] = ord("9") if original != "9" else ord("8")
    journal.write_bytes(payload)
    return {
        "file": "runs.jsonl",
        "mutation": "one numeric byte changed in a copied observation",
        "original_byte": original,
        "replacement_byte": chr(payload[position]),
    }


def _inventory(
    roots: Iterable[Path],
    *,
    source: Path,
    source_snapshot: Any,
    source_facts: tuple[int, str],
    remaining_bytes: int,
) -> list[dict[str, Any]]:
    inventory = []
    seen: set[Path] = set()
    for raw_bundle in roots:
        bundle = raw_bundle.resolve()
        if bundle in seen:
            continue
        seen.add(bundle)
        if bundle == source:
            snapshot = source_snapshot
            bundle_bytes, tree_hash = source_facts
        else:
            bundle_bytes, tree_hash = _tree_facts(bundle, max_bytes=remaining_bytes)
            remaining_bytes -= bundle_bytes
            snapshot = inspect_bundle(bundle, verify=True, max_bytes=bundle_bytes + 1)
        if snapshot.report is None:
            raise ValueError("inventory roots must contain completed qualification reports")
        procedures = sorted({metric.procedure for metric in snapshot.report.metrics})
        inventory.append(
            {
                "bundle": str(bundle),
                "workload_digest": snapshot.report.workload_digest,
                "qualification": snapshot.qualification,
                "procedures": procedures,
                "bytes": bundle_bytes,
                "tree_hash": tree_hash,
                "verification": "verified public reader",
            }
        )
    return inventory


def rehearse(
    source: Path,
    destination: Path,
    *,
    inventory_roots: Iterable[Path] = (),
) -> dict[str, Any]:
    """Copy, corrupt, reject, restore, and independently recompute one bundle."""
    started = time.monotonic()
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_dir():
        raise ValueError("source must be an existing evidence bundle")
    if not _outside(destination, source):
        raise ValueError("destination must be outside the validated source bundle")
    source_bytes, source_before = _tree_facts(source)
    retained_copy_bytes = 3 * source_bytes
    accounted_bytes = retained_copy_bytes + source_bytes
    if accounted_bytes > MAX_SOURCE_BYTES:
        raise ValueError("source and three incident copies exceed the 32 MiB rehearsal limit")
    source_snapshot = inspect_bundle(source, verify=True)
    if source_snapshot.report is None:
        raise ValueError("source must contain a completed qualification report")
    destination.mkdir(parents=True, exist_ok=False)
    original_copy = destination / "original-copy"
    corrupted_copy = destination / "corrupted-copy"
    restored_copy = destination / "restored-copy"
    shutil.copytree(source, original_copy)
    shutil.copytree(source, corrupted_copy)
    mutation = _corrupt_journal(corrupted_copy)

    rejection = None
    try:
        inspect_bundle(corrupted_copy, verify=True)
    except ValueError as error:
        rejection = str(error)
    if rejection is None:
        raise RuntimeError("public evidence reader accepted the corrupted bundle")

    shutil.copytree(original_copy, restored_copy)
    restored = inspect_bundle(restored_copy, verify=True)
    if restored.qualification != source_snapshot.qualification or restored.report != source_snapshot.report:
        raise RuntimeError("restored evidence did not independently recompute the retained result")
    _, source_after = _tree_facts(source)
    if source_after != source_before:
        raise RuntimeError("validated source evidence changed during the rehearsal")
    affected_procedures = sorted({metric.procedure for metric in source_snapshot.report.metrics})
    affected_inventory = _inventory(
        inventory_roots or (source,),
        source=source,
        source_snapshot=source_snapshot,
        source_facts=(source_bytes, source_before),
        remaining_bytes=MAX_SOURCE_BYTES - accounted_bytes,
    )
    elapsed = time.monotonic() - started
    if elapsed > MAX_SECONDS:
        raise RuntimeError("incident rehearsal exceeded its 90 second bound")
    result = {
        "schema": "gibbsiq-incident-rehearsal-v1",
        "classification": "artifact-integrity incident",
        "impact": "fake local impact example; only the corrupted copy is untrusted",
        "source": {
            "path": str(source),
            "bytes": source_bytes,
            "tree_hash_before": source_before,
            "tree_hash_after": source_after,
            "qualification": source_snapshot.qualification,
            "workload_digest": source_snapshot.report.workload_digest,
        },
        "affected_inventory": affected_inventory,
        "affected_contract": record_to_dict(source_snapshot.plan.workload.contract),
        "affected_procedures": affected_procedures,
        "containment": {
            "claim_status": "suspended for corrupted copy",
            "validated_original_modified": False,
            "external_notice_sent": False,
            "private_payload_status": "not_assessed; input is copied byte-for-byte only to local output",
            "action": "Reject the copy, retain its hash and error, and serve no claim from it.",
        },
        "corruption": {**mutation, "reader_result": "rejected", "reason": rejection},
        "reverification": {
            "copy": "restored-copy",
            "reader": "gibbsiq.qualification.artifacts.inspect_bundle(verify=True)",
            "qualification": restored.qualification,
            "report_recomputed_equal": restored.report == source_snapshot.report,
            "tree_hash": _tree_facts(restored_copy)[1],
        },
        "elapsed_seconds": elapsed,
        "limits": {
            "max_seconds": MAX_SECONDS,
            "max_retained_and_inventory_bytes": MAX_SOURCE_BYTES,
            "retained_copy_bytes": retained_copy_bytes,
            "source_and_copy_bytes": accounted_bytes,
        },
        "limitations": [
            "This is an explicit fake local impact scenario, not an actual user incident.",
            "It exercises artifact corruption; it does not simulate a leak, dependency compromise, or hardware event.",
            "No external notice was sent and no publication state changed.",
        ],
    }
    (destination / "incident.json").write_bytes(canonical_json(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--inventory-root", action="append", type=Path, default=[])
    args = parser.parse_args()
    print(
        json.dumps(
            rehearse(args.source, args.output, inventory_roots=args.inventory_root),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
