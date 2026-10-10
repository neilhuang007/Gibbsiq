"""Create a bounded, read-only evidence and retention inventory."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Iterable

from gibbsiq.qualification.artifacts import inspect_bundle

_BUNDLE_BASE = frozenset({"workload.json", "plan.json", "environment.json", "runs.jsonl"})
_DEFAULT_MAX_BYTES = 256 * 1024 * 1024
_DEFAULT_MAX_ENTRIES = 20_000


def _is_link(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(attributes & reparse)


def _explicit_path(value: str | Path, *, name: str) -> Path:
    raw = Path(value)
    if ".." in raw.parts:
        raise ValueError(f"{name} must not contain parent traversal")
    if not raw.exists():
        raise ValueError(f"{name} does not exist: {raw}")
    if _is_link(raw):
        raise ValueError(f"{name} must not be a link")
    return raw.resolve()


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def _walk_roots(
    roots: tuple[Path, ...], *, max_total_bytes: int, max_entries: int
) -> tuple[dict[Path, frozenset[str]], dict[Path, int], int, int]:
    file_names: dict[Path, set[str]] = {}
    direct_bytes: dict[Path, int] = {}
    total_bytes = 0
    seen_entries: set[Path] = set()
    walked_directories: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            raise ValueError("inventory roots must be directories")
        for parent, child_dirs, files in os.walk(root, followlinks=False):
            current = Path(parent)
            if current in walked_directories:
                child_dirs.clear()
                continue
            walked_directories.add(current)
            names = file_names.setdefault(current, set())
            direct_bytes.setdefault(current, 0)
            for name in child_dirs:
                child = current / name
                if _is_link(child):
                    raise ValueError("inventory scope contains a linked directory")
                seen_entries.add(child)
            for name in files:
                child = current / name
                if _is_link(child) or not child.is_file():
                    raise ValueError("inventory scope contains an unsafe file")
                names.add(name)
                if child not in seen_entries:
                    size = child.stat().st_size
                    direct_bytes[current] += size
                    total_bytes += size
                seen_entries.add(child)
            if len(seen_entries) > max_entries:
                raise ValueError("inventory exceeds entry budget")
            if total_bytes > max_total_bytes:
                raise ValueError("inventory exceeds byte budget")

    subtree_bytes = dict(direct_bytes)
    for directory in sorted(subtree_bytes, key=lambda path: len(path.parts), reverse=True):
        if directory.parent in subtree_bytes:
            subtree_bytes[directory.parent] += subtree_bytes[directory]
    return (
        {directory: frozenset(names) for directory, names in file_names.items()},
        subtree_bytes,
        len(seen_entries),
        total_bytes,
    )


def inventory_evidence(
    roots: Iterable[str | Path],
    *,
    private_paths: Iterable[str | Path] = (),
    deletion_targets: Iterable[str | Path] = (),
    large_bytes: int = 64 * 1024 * 1024,
    max_total_bytes: int = _DEFAULT_MAX_BYTES,
    max_entries: int = _DEFAULT_MAX_ENTRIES,
) -> dict[str, Any]:
    """Inspect schema-1 bundles under explicit roots and plan retention without writes."""
    for name, value in (
        ("large_bytes", large_bytes),
        ("max_total_bytes", max_total_bytes),
        ("max_entries", max_entries),
    ):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    scope = tuple(_explicit_path(path, name="inventory root") for path in roots)
    if not scope:
        raise ValueError("at least one explicit inventory root is required")
    if len(set(scope)) != len(scope):
        raise ValueError("inventory roots must be unique")
    private = tuple(_explicit_path(path, name="private path") for path in private_paths)
    targets = tuple(_explicit_path(path, name="deletion target") for path in deletion_targets)
    for path in (*private, *targets):
        if not _inside(path, scope):
            raise ValueError("private paths and deletion targets must be inside an inventory root")

    file_names, subtree_bytes, entries, total_bytes = _walk_roots(
        scope, max_total_bytes=max_total_bytes, max_entries=max_entries
    )
    bundles: list[dict[str, Any]] = []
    for directory, names in sorted(file_names.items(), key=lambda item: str(item[0])):
        if not _BUNDLE_BASE.issubset(names):
            continue
        bundle_bytes = subtree_bytes[directory]
        item: dict[str, Any] = {
            "path": str(directory),
            "bytes": bundle_bytes,
            "private": any(
                directory == path or directory.is_relative_to(path) or path.is_relative_to(directory)
                for path in private
            ),
            "large": bundle_bytes >= large_bytes,
            "schema": 1,
        }
        try:
            snapshot = inspect_bundle(
                directory, verify=True, max_bytes=min(max_total_bytes, bundle_bytes + 1)
            )
        except (OSError, ValueError) as error:
            item.update(status="corrupt", certified=False, error=str(error))
        else:
            item.update(
                status="supported",
                certified=True,
                execution=snapshot.execution,
                qualification=snapshot.qualification,
                payload_validation=snapshot.payload_validation,
            )
        bundles.append(item)

    return {
        "schema": "gibbsiq.retention-inventory.v1",
        "mode": "dry-run",
        "roots": [str(path) for path in scope],
        "entries": entries,
        "bytes": total_bytes,
        "bundles": bundles,
        "dry_run_deletion_targets": [str(path) for path in targets],
        "mutations_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", required=True, type=Path)
    parser.add_argument("--private", action="append", default=[], type=Path)
    parser.add_argument("--delete-target", action="append", default=[], type=Path)
    parser.add_argument("--large-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--max-total-bytes", type=int, default=_DEFAULT_MAX_BYTES)
    parser.add_argument("--max-entries", type=int, default=_DEFAULT_MAX_ENTRIES)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = inventory_evidence(
        args.root,
        private_paths=args.private,
        deletion_targets=args.delete_target,
        large_bytes=args.large_bytes,
        max_total_bytes=args.max_total_bytes,
        max_entries=args.max_entries,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"retention_inventory: {error}", file=sys.stderr)
        raise SystemExit(2) from error
