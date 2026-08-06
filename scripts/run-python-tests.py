#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import trace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    coverage_dir = Path(args.coverage_dir).resolve()
    coverage_dir.mkdir(parents=True, exist_ok=True)

    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test_*.py"
    )
    runner = unittest.TextTestRunner(verbosity=2)
    tracer = trace.Trace(
        count=True,
        trace=False,
        ignoredirs=[
            sys.prefix,
            sys.base_prefix,
            str(Path(unittest.__file__).resolve().parent),
        ],
    )
    result = tracer.runfunc(runner.run, suite)
    print("\n===== PYTHON LINE COVERAGE =====")
    tracer.results().write_results(
        show_missing=True,
        summary=True,
        coverdir=str(coverage_dir),
    )
    print(f"PYTHON_TESTS_RUN={result.testsRun}")
    print(f"PYTHON_TEST_FAILURES={len(result.failures)}")
    print(f"PYTHON_TEST_ERRORS={len(result.errors)}")
    print("PYTHON_BEHAVIOR_SUITE=" + ("PASS" if result.wasSuccessful() else "FAIL"))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
