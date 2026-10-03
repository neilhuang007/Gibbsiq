"""Acquire the two exact pinned Z1T-0 checkpoint artifacts safely."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Callable
import urllib.request

from gibbsiq.qualification.adapters.model_preflight import (
    PINNED_CHECKPOINT_REVISION,
    RELEASED_CHECKPOINT_SHA256,
    RELEASED_CONFIG_BYTES,
    RELEASED_CONFIG_SHA256,
    RELEASED_Z1T0,
)

REVISION = PINNED_CHECKPOINT_REVISION
BASE_URL = f"https://huggingface.co/Extropic-AI/Z1T-0/resolve/{REVISION}"
DISK_RESERVE_BYTES = 4 * 1024**3
READ_TIMEOUT_SECONDS = 60.0
TOTAL_TIMEOUT_SECONDS = 20 * 60.0
CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    name: str
    url: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class AcquisitionResult:
    name: str
    path: str
    bytes: int
    sha256: str
    status: str


ARTIFACTS = (
    ArtifactSpec(
        "config.json",
        f"{BASE_URL}/config.json",
        RELEASED_CONFIG_BYTES,
        RELEASED_CONFIG_SHA256,
    ),
    ArtifactSpec(
        "model.eqx",
        f"{BASE_URL}/model.eqx",
        RELEASED_Z1T0.checkpoint_bytes,
        RELEASED_CHECKPOINT_SHA256,
    ),
)


def _identity(path: Path, *, maximum: int | None = None) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_BYTES):
            total += len(chunk)
            if maximum is not None and total > maximum:
                return total, ""
            digest.update(chunk)
    return total, digest.hexdigest()


def _valid_existing(path: Path, spec: ArtifactSpec) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    if path.stat().st_size != spec.size:
        return False
    size, digest = _identity(path, maximum=spec.size)
    return size == spec.size and digest == spec.sha256


def acquire_artifact(
    spec: ArtifactSpec,
    destination: Path,
    *,
    opener: Callable[..., object] = urllib.request.urlopen,
    disk_usage: Callable[[Path], object] = shutil.disk_usage,
    clock: Callable[[], float] = time.monotonic,
) -> AcquisitionResult:
    """Download one fixed artifact to a temporary file, verify it, then publish."""
    if not isinstance(spec, ArtifactSpec):
        raise ValueError("spec must be ArtifactSpec")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / spec.name
    if target.exists() or target.is_symlink():
        if _valid_existing(target, spec):
            return AcquisitionResult(spec.name, str(target), spec.size, spec.sha256, "existing-valid")
        raise FileExistsError(f"unexpected existing artifact is invalid and was not overwritten: {target}")

    free = int(disk_usage(destination).free)
    required = spec.size + DISK_RESERVE_BYTES
    if free < required:
        raise OSError(f"insufficient free disk: need {required} bytes, found {free}")

    temporary: Path | None = None
    started = clock()
    try:
        with tempfile.NamedTemporaryFile(
            mode="xb", dir=destination, prefix=spec.name + ".", suffix=".part", delete=False
        ) as output:
            temporary = Path(output.name)
            request = urllib.request.Request(spec.url, headers={"User-Agent": "gibbsiq-pinned-checkpoint/1"})
            with opener(request, timeout=READ_TIMEOUT_SECONDS) as response:
                digest = hashlib.sha256()
                total = 0
                while True:
                    if clock() - started > TOTAL_TIMEOUT_SECONDS:
                        raise TimeoutError("checkpoint acquisition exceeded 1200 seconds")
                    chunk = response.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > spec.size:
                        raise ValueError("download exceeds expected byte count")
                    output.write(chunk)
                    digest.update(chunk)
            if total != spec.size:
                raise ValueError(f"download byte count mismatch: expected {spec.size}, received {total}")
            actual_digest = digest.hexdigest()
            if actual_digest != spec.sha256:
                raise ValueError("download SHA-256 mismatch")
            output.flush()
            os.fsync(output.fileno())
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"artifact appeared during download and was not overwritten: {target}")
        os.replace(temporary, target)
        temporary = None
        return AcquisitionResult(spec.name, str(target), total, actual_digest, "downloaded")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def acquire_checkpoint(destination: Path) -> tuple[AcquisitionResult, ...]:
    return tuple(acquire_artifact(spec, destination) for spec in ARTIFACTS)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="existing or new private checkpoint directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    results = acquire_checkpoint(arguments.destination)
    print(
        json.dumps(
            {"revision": REVISION, "artifacts": [asdict(result) for result in results]},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
