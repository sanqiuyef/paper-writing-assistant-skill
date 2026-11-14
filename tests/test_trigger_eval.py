"""Lexical trigger baseline must stay aligned with the committed trigger cases."""

from __future__ import annotations

import unittest

import evaluate_triggers as trigger


class TriggerEvaluationTest(unittest.TestCase):
    def test_lexical_baseline_accuracy(self) -> None:
        cases = trigger.load_cases()
        terms = trigger.description_terms()
        predictions = {
            case["id"]: trigger.lexical_predict(case["prompt"], terms) for case in cases
        }
        result = trigger.score(cases, predictions)
        self.assertEqual(result["accuracy"], 1.0, result["misses"])


if __name__ == "__main__":
    unittest.main()
