"""Generate deterministic TM-IMP-001 factor-JSON and graph-frontend evidence.

Oracle rule: every expected energy in the emitted fixtures is evaluated
directly from the source document or graph rows; no importer, conversion,
or model helper participates in producing an expected value.
"""

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
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import __version__  # noqa: E402
from gibbsiq.importers import (  # noqa: E402
    FACTOR_GRAPH_SCHEMA_VERSION,
    factor_json_from_program,
    program_from_factor_json,
    program_from_networkx,
)
from gibbsiq.model import encode_variable_label  # noqa: E402

RUN_ID = "2026-07-21-factor-json-and-networkx"
SEED = 20_260_721
ABSOLUTE_TOLERANCE = 1e-9
DOCUMENT_CASE_COUNT = 36
GRAPH_CASE_COUNT = 16
DEFAULT_OUTPUT = REPO_ROOT / "reference" / "00-roadmap" / "artifacts" / "tm-imp-001" / RUN_ID
SOURCE_PATHS = (
    "pyproject.toml",
    "reference/02-interfaces/factor-graph-json-v1.md",
    "src/gibbsiq/__init__.py",
    "src/gibbsiq/conversions.py",
    "src/gibbsiq/importers.py",
    "src/gibbsiq/model.py",
    "src/gibbsiq/program.py",
    "test_suite/tests/test_importers.py",
    "tools/generate_tm_imp_001_artifacts.py",
)
LABEL_POOL = (
    "a",
    "b",
    "c",
    "node",
    "é",
    "linear",
    "quadratic",
    0,
    1,
    7,
    -3,
    2.5,
    -0.5,
    True,
    False,
    None,
    ("t", 1),
    ("t", 2),
    ("c", 2),
    b"\x01",
    b"raw",
    frozenset({"m"}),
    frozenset({"x", "y"}),
    (("nested",), 3.5),
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
    completed = subprocess.run(["git", *arguments], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


class _GraphRows:
    """Duck-typed stand-in for the NetworkX Graph surface the frontend consumes."""

    def __init__(
        self,
        nodes: list[tuple[Any, dict[str, Any]]],
        edges: list[tuple[Any, Any, dict[str, Any]]],
        graph: dict[str, Any],
    ):
        self._nodes, self._edges, self.graph = nodes, edges, graph

    def is_directed(self) -> bool:
        return False

    def is_multigraph(self) -> bool:
        return False

    def nodes(self, data: bool = False) -> list[Any]:
        return list(self._nodes) if data else [label for label, _ in self._nodes]

    def edges(self, data: bool = False) -> list[Any]:
        if data:
            return [(left, right, attrs) for left, right, attrs in self._edges]
        return [(left, right) for left, right, _ in self._edges]


def _distinct_labels(rng: random.Random, count: int) -> list[Any]:
    chosen: list[Any] = []
    for label in rng.sample(LABEL_POOL, len(LABEL_POOL)):
        if len(chosen) == count:
            break
        if all(not (label == existing) for existing in chosen):
            chosen.append(label)
    if len(chosen) != count:
        raise AssertionError("label pool exhausted")
    return chosen


def _direct_document_energy(document: Mapping[str, Any], values: Sequence[int]) -> float:
    terms = [document["offset"]]
    for factor in document["factors"]:
        term = factor["coefficient"]
        for position in factor["scope"]:
            term *= values[position]
        terms.append(term)
    return math.fsum(terms)


def _direct_graph_energy(
    nodes: Sequence[tuple[Any, Mapping[str, Any]]],
    edges: Sequence[tuple[Any, Any, Mapping[str, Any]]],
    offset: float,
    values: Mapping[Any, int],
) -> float:
    terms = [offset]
    terms.extend(attrs.get("bias", 0.0) * values[label] for label, attrs in nodes)
    terms.extend(attrs["weight"] * values[left] * values[right] for left, right, attrs in edges)
    return math.fsum(terms)


def _random_document(rng: random.Random, vartype: str) -> dict[str, Any]:
    count = rng.randint(0, 5)
    labels = _distinct_labels(rng, count)
    factors: list[dict[str, Any]] = []
    for position in range(count):
        if rng.random() < 0.7:
            factors.append({"scope": [position], "coefficient": rng.uniform(-3, 3)})
    for left, right in itertools.combinations(range(count), 2):
        if rng.random() < 0.5:
            factors.append({"scope": [left, right], "coefficient": rng.uniform(-3, 3)})
    rng.shuffle(factors)
    document: dict[str, Any] = {
        "format": "gibbsiq-factor-graph",
        "schema_version": FACTOR_GRAPH_SCHEMA_VERSION,
        "vartype": vartype,
        "offset": rng.uniform(-2, 2),
        "variables": [encode_variable_label(label) for label in labels],
        "factors": factors,
    }
    clamp_domain = (0, 1) if vartype == "BINARY" else (-1, 1)
    clamps = [
        {"position": position, "value": rng.choice(clamp_domain)}
        for position in range(count)
        if rng.random() < 0.25
    ]
    if clamps:
        document["clamps"] = clamps
    if count and rng.random() < 0.4:
        document["coordinates"] = [
            {"position": position, "coordinate": [float(rng.randint(0, 9)), float(rng.randint(0, 9))]}
            for position in range(count)
        ]
    if rng.random() < 0.5:
        document["metadata"] = {"trial": rng.randint(0, 10**6), "tag": rng.choice(["x", "y"])}
    return document


def _document_cases(rng: random.Random) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    checked = 0
    max_error = 0.0
    corpus = hashlib.sha256()
    for index in range(DOCUMENT_CASE_COUNT):
        vartype = "SPIN" if index % 2 == 0 else "BINARY"
        document = _random_document(rng, vartype)
        wire_copy = json.loads(json.dumps(document, sort_keys=True, allow_nan=False))
        program = program_from_factor_json(wire_copy)
        domain = (-1, 1) if vartype == "SPIN" else (0, 1)
        size = len(document["variables"])
        energy_table = []
        for values in itertools.product(domain, repeat=size):
            expected = _direct_document_energy(document, values)
            actual = program.model.energy(dict(zip(program.model.variables, values)), vartype=vartype)
            max_error = max(max_error, abs(expected - actual))
            checked += 1
            energy_table.append({"assignment": list(values), "energy": expected})
        exported = factor_json_from_program(program)
        reexported = factor_json_from_program(program_from_factor_json(exported))
        if reexported != exported:
            raise AssertionError(f"export is not a fixed point for document case {index}")
        corpus.update(json.dumps(exported, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
        cases.append(
            {
                "case_id": f"document-{index:02d}",
                "document": document,
                "energy_table": energy_table,
                "exported": exported,
            }
        )
    if max_error > ABSOLUTE_TOLERANCE:
        raise AssertionError(f"document oracle exceeded tolerance: {max_error!r}")
    summary = {
        "assignments_checked": checked,
        "case_count": DOCUMENT_CASE_COUNT,
        "export_corpus_sha256": corpus.hexdigest(),
        "max_absolute_error": max_error,
    }
    return cases, summary


def _graph_cases(rng: random.Random) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    checked = 0
    max_error = 0.0
    for index in range(GRAPH_CASE_COUNT):
        count = rng.randint(0, 5)
        labels = _distinct_labels(rng, count)
        nodes = [(label, {"bias": rng.uniform(-2, 2)} if rng.random() < 0.7 else {}) for label in labels]
        edges = []
        for left, right in itertools.combinations(range(count), 2):
            if rng.random() < 0.5:
                pair = (labels[left], labels[right]) if rng.random() < 0.5 else (labels[right], labels[left])
                edges.append((*pair, {"weight": rng.uniform(-2, 2)}))
        offset = rng.uniform(-1, 1)
        program = program_from_networkx(_GraphRows(nodes, edges, {"offset": offset}), vartype="SPIN")
        shuffled_nodes = nodes[:]
        shuffled_edges = edges[:]
        rng.shuffle(shuffled_nodes)
        rng.shuffle(shuffled_edges)
        shuffled = program_from_networkx(
            _GraphRows(shuffled_nodes, shuffled_edges, {"offset": offset}), vartype="SPIN"
        )
        if factor_json_from_program(program) != factor_json_from_program(shuffled):
            raise AssertionError(f"graph import is insertion-order dependent for case {index}")
        energy_table = []
        for values in itertools.product((-1, 1), repeat=count):
            sample = dict(zip(program.model.variables, values))
            expected = _direct_graph_energy(nodes, edges, offset, sample)
            actual = program.model.energy(sample)
            max_error = max(max_error, abs(expected - actual))
            checked += 1
            energy_table.append({"assignment": list(values), "energy": expected})
        cases.append(
            {
                "case_id": f"graph-{index:02d}",
                "edges": [
                    [encode_variable_label(left), encode_variable_label(right), attrs]
                    for left, right, attrs in edges
                ],
                "energy_table": energy_table,
                "exported": factor_json_from_program(program),
                "graph_attributes": {"offset": offset},
                "nodes": [[encode_variable_label(label), attrs] for label, attrs in nodes],
            }
        )
    if max_error > ABSOLUTE_TOLERANCE:
        raise AssertionError(f"graph oracle exceeded tolerance: {max_error!r}")
    summary = {
        "assignments_checked": checked,
        "case_count": GRAPH_CASE_COUNT,
        "max_absolute_error": max_error,
    }
    return cases, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args()
    output: Path = arguments.output
    if output.exists() and not arguments.overwrite:
        raise SystemExit(f"{output} exists; pass --overwrite to regenerate")
    output.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    rng = random.Random(SEED)
    document_cases, document_summary = _document_cases(rng)
    graph_cases, graph_summary = _graph_cases(rng)
    elapsed = time.perf_counter() - started

    try:
        import networkx

        networkx_version = networkx.__version__
    except ImportError:
        networkx_version = None

    _write_json(output / "document-fixtures.json", {"cases": document_cases, "run_id": RUN_ID})
    _write_json(output / "graph-fixtures.json", {"cases": graph_cases, "run_id": RUN_ID})
    _write_json(
        output / "oracle-results.json",
        {
            "documents": document_summary,
            "graphs": graph_summary,
            "oracle": (
                "enumerate every assignment and sum the raw document factors or graph "
                "bias/weight rows directly; importer and model outputs are compared "
                "against those sums and never used to produce them"
            ),
            "run_id": RUN_ID,
            "tolerance": ABSOLUTE_TOLERANCE,
        },
    )
    _write_json(
        output / "generation-config.json",
        {
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "classification": {
                "energies": "computed",
                "seed": "declared deterministic fixture input",
                "tolerance": "assumed project-wide floating comparison tolerance from CLAUDE.md",
            },
            "document_case_count": DOCUMENT_CASE_COUNT,
            "factor_graph_schema_version": FACTOR_GRAPH_SCHEMA_VERSION,
            "generator_seed": SEED,
            "graph_case_count": GRAPH_CASE_COUNT,
            "label_pool_size": len(LABEL_POOL),
            "reproduction_command": "python tools/generate_tm_imp_001_artifacts.py --overwrite",
            "rng": "Python random.Random (MT19937)",
            "run_id": RUN_ID,
            "variable_count_range": [0, 5],
        },
    )
    _write_json(
        output / "environment.json",
        {
            "gibbsiq_version": __version__,
            "git_head": _git_value("rev-parse", "HEAD"),
            "implementation": platform.python_implementation(),
            "networkx_version": networkx_version,
            "os_name": os.name,
            "platform": platform.platform(),
            "python": sys.version,
            "run_id": RUN_ID,
            "task_id": "TM-IMP-001",
            "timing_seconds": {"generation": elapsed},
        },
    )
    source_rows = [
        {
            "bytes": (REPO_ROOT / path).stat().st_size,
            "path": path,
            "sha256": _sha256(REPO_ROOT / path),
        }
        for path in SOURCE_PATHS
    ]
    aggregate = hashlib.sha256("".join(row["sha256"] for row in source_rows).encode("ascii")).hexdigest()
    _write_json(
        output / "source-files.json",
        {"aggregate_sha256": aggregate, "algorithm": "SHA-256", "files": source_rows},
    )
    manifest_rows = [
        {"bytes": path.stat().st_size, "path": path.name, "sha256": _sha256(path)}
        for path in sorted(output.glob("*.json"))
        if path.name != "manifest.json"
    ]
    _write_json(
        output / "manifest.json",
        {"algorithm": "SHA-256", "files": manifest_rows, "run_id": RUN_ID},
    )
    print(f"wrote {len(manifest_rows) + 1} artifact files to {output}")
    print(f"documents: {document_summary}")
    print(f"graphs: {graph_summary}")


if __name__ == "__main__":
    main()
