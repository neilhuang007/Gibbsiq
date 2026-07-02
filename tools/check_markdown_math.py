"""Check Markdown math blocks for renderer-safe formatting.

The project renderer is sensitive to one-line display math and raw angle
brackets inside LaTeX. This script checks authored Markdown files while skipping
paper transcripts and generated source notes that may preserve upstream style.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_PATHS = [
    Path("README.md"),
    Path("PROJECT_BRIEF.md"),
    Path("CLAUDE.md"),
    Path("AGENTS.md"),
    Path("spec.md"),
    Path("reference"),
]

SKIP_PARTS = {"papers"}
INLINE_CODE_RE = re.compile(r"`[^`]*`")


def _iter_markdown(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".md":
            files.append(path)
        elif path.is_dir():
            for candidate in path.rglob("*.md"):
                if any(part in SKIP_PARTS for part in candidate.parts):
                    continue
                files.append(candidate)
    return sorted(set(files))


def _check_file(path: Path) -> list[str]:
    errors: list[str] = []
    in_code_fence = False
    in_display_math = False

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue

        line_without_code = INLINE_CODE_RE.sub("", line)

        if "$$" in line_without_code:
            if stripped != "$$":
                errors.append(
                    f"{path}:{line_number}: display math delimiter must be alone on its line"
                )
                continue
            in_display_math = not in_display_math
            continue

        if in_display_math and ("<" in line or ">" in line):
            errors.append(
                f"{path}:{line_number}: use \\lt or \\gt inside display math, not raw < or >"
            )

    if in_display_math:
        errors.append(f"{path}: unclosed display math block")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, default=DEFAULT_PATHS)
    args = parser.parse_args()

    errors: list[str] = []
    for path in _iter_markdown(args.paths):
        errors.extend(_check_file(path))

    if errors:
        for error in errors:
            print(error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
