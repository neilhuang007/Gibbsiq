"""Run integration tests with spawn-safe startup and fail on skipped tests."""

from __future__ import annotations

import argparse
import io
from pathlib import Path
import sys
import unittest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pattern", default="test*.py", help="unittest discovery filename pattern")
    args = parser.parse_args()

    suite = unittest.defaultTestLoader.discover("test_suite/tests", pattern=args.pattern)
    if suite.countTestCases() == 0:
        raise RuntimeError("no tests discovered for extras profile")
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    output = log.getvalue()
    print(output, end="")
    Path("test-results").mkdir(exist_ok=True)
    Path("test-results/unittest.log").write_text(output[-2_000_000:], encoding="utf-8")

    if result.skipped:
        print("\nSkipped tests are forbidden in the extras profile:", file=sys.stderr)
        for test, reason in result.skipped:
            print(f"- {test.id()}: {reason}", file=sys.stderr)

    return int(not result.wasSuccessful() or bool(result.skipped))


if __name__ == "__main__":
    raise SystemExit(main())
