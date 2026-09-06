#!/usr/bin/env python3
"""Unified E2E Test Runner for AgentForge.

Executes the 4-tier requirement-driven E2E test suite:
- Tier 1: Feature Coverage (Isolation)
- Tier 2: Boundary & Corner Cases
- Tier 3: Cross-Feature Combinations
- Tier 4: Real-World Application Scenarios

Usage:
    python3 tests/e2e/run_tests.py               # Run all 4 tiers
    python3 tests/e2e/run_tests.py --tier 1      # Run Tier 1 only
    python3 tests/e2e/run_tests.py --tier 2      # Run Tier 2 only
    python3 tests/e2e/run_tests.py --tier 3      # Run Tier 3 only
    python3 tests/e2e/run_tests.py --tier 4      # Run Tier 4 only
    python3 tests/e2e/run_tests.py -v            # Verbose pytest output
    python3 tests/e2e/run_tests.py -k "auth"     # Filter by keyword
"""

import argparse
import os
import subprocess
import sys
import time
from typing import Dict, List, Tuple


TIER_MAPPING = {
    1: ("Tier 1: Feature Coverage (Isolation)", "tests/e2e/test_tier1_features.py"),
    2: ("Tier 2: Boundary & Corner Cases", "tests/e2e/test_tier2_boundaries.py"),
    3: ("Tier 3: Cross-Feature Combinations", "tests/e2e/test_tier3_combinations.py"),
    4: ("Tier 4: Real-World Application Scenarios", "tests/e2e/test_tier4_scenarios.py"),
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AgentForge E2E 4-Tier Test Runner")
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4],
        help="Select specific tier to run (default: all tiers)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose pytest output",
    )
    parser.add_argument(
        "-k", "--filter",
        type=str,
        default=None,
        help="Filter tests by expression/keyword",
    )
    return parser.parse_args()


def run_tier(tier_num: int, tier_name: str, test_file: str, verbose: bool, filter_kw: str | None) -> Tuple[int, float, str]:
    print(f"\n{'='*75}")
    print(f"  RUNNING {tier_name.upper()}")
    print(f"  Target File: {test_file}")
    print(f"{'='*75}")

    cmd = [sys.executable, "-m", "pytest", test_file]
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    if filter_kw:
        cmd.extend(["-k", filter_kw])

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time

    output = result.stdout + result.stderr
    print(output.strip())

    return result.returncode, duration, output


def main() -> int:
    args = parse_arguments()
    selected_tiers = [args.tier] if args.tier else [1, 2, 3, 4]

    results: Dict[int, Dict[str, any]] = {}
    overall_exit_code = 0
    total_suite_start = time.time()

    print("\n" + "#"*75)
    print("  AGENTFORGE E2E 4-TIER TEST SUITE EXECUTION")
    print("#"*75)

    for tier_num in selected_tiers:
        tier_name, test_file = TIER_MAPPING[tier_num]
        return_code, duration, output = run_tier(
            tier_num, tier_name, test_file, args.verbose, args.filter
        )

        passed = return_code == 0
        if not passed:
            overall_exit_code = 1

        results[tier_num] = {
            "name": tier_name,
            "file": test_file,
            "passed": passed,
            "duration": duration,
            "return_code": return_code,
            "output": output,
        }

    total_suite_duration = time.time() - total_suite_start

    # Print Summary Table
    print("\n\n" + "="*75)
    print(f"{'TIER':<8} | {'TIER NAME':<42} | {'DURATION':<10} | {'STATUS'}")
    print("-"*75)

    total_passed = 0
    for tier_num, res in results.items():
        status_str = "PASS [OK]" if res["passed"] else "FAIL [X]"
        if res["passed"]:
            total_passed += 1
        print(f"Tier {tier_num:<3} | {res['name']:<42} | {res['duration']:>6.2f}s    | {status_str}")

    print("-"*75)
    print(f"Total Tiers Executed: {len(results)} | Passed: {total_passed} | Failed: {len(results) - total_passed}")
    print(f"Total Test Suite Duration: {total_suite_duration:.2f}s")
    print("="*75 + "\n")

    if overall_exit_code == 0:
        print(">> ALL E2E TIERS PASSED SUCCESSFULLY (100% REQUIREMENT CONFORMANCE)")
    else:
        print(">> WARNING: ONE OR MORE E2E TIERS FAILED VERIFICATION")

    return overall_exit_code


if __name__ == "__main__":
    sys.exit(main())
