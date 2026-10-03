"""Run the frozen bounded tiny-model policy search.

This uses generated parameters and synthetic tokens. It validates a local
software emulation profile and does not claim physical Z1 execution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from gibbsiq.qualification.adapters.model_search import tiny_model_search_plan, tune_tiny_model


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    parser.add_argument("--max-bytes", type=int, default=64 * 1024 * 1024)
    args = parser.parse_args(argv)
    plan = tiny_model_search_plan(max_seconds=args.max_seconds, max_bytes=args.max_bytes)
    result = tune_tiny_model(destination=args.output, plan=plan)
    print(
        json.dumps(
            {
                "lifecycle": result["lifecycle"],
                "selected": result["selected"],
                "attempts": len(result["attempts"]),
                "report": str(args.output / "search-report.json"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
