"""Regression suite for the committed synthetic cases."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from run_regression import evaluate

CASES = Path(__file__).resolve().parent / "regression_cases.json"


class RegressionCasesTest(unittest.TestCase):
    def test_committed_cases_match_expected(self) -> None:
        payload = json.loads(CASES.read_text(encoding="utf-8"))
        failures = []
        for case in payload["cases"]:
            actual = evaluate(case)
            for tool, verdict in actual.items():
                expected = case.get("checks", {}).get(tool, {}).get("verdict")
                if expected is not None and expected != verdict:
                    failures.append((case["id"], tool, expected, verdict))
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
