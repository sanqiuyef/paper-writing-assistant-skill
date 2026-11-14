"""Deterministic fact-integrity checks between original and revised text."""

from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fact_integrity_check as fact  # noqa: E402


def run_check(original: str, revised: str, terms: str = "", no_directions: bool = False) -> dict:
    with tempfile.TemporaryDirectory() as temp:
        original_path = Path(temp) / "original.txt"
        revised_path = Path(temp) / "revised.txt"
        original_path.write_text(original, encoding="utf-8")
        revised_path.write_text(revised, encoding="utf-8")
        args = argparse.Namespace(
            original=str(original_path),
            revised=str(revised_path),
            terms=terms,
            terms_file=None,
            bracket_citations=False,
            no_directions=no_directions,
        )
        return fact.run(args)


def codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"]}


class FactIntegrityTest(unittest.TestCase):
    def test_identical_text_passes(self) -> None:
        text = "本文在21场降雨上测试，RMSE 为 8.78 mm，PICP 为 0.8465。"
        result = run_check(text, text)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["stats"]["numbers_original"], 3)

    def test_missing_number_fails(self) -> None:
        result = run_check("RMSE 为 8.78 mm。", "RMSE 降到 8.7 mm。")
        self.assertIn("FACT_NUMBER_MISSING", codes(result))
        self.assertEqual(result["verdict"], "FAIL")

    def test_added_number_fails(self) -> None:
        result = run_check("样本为 21 场。", "样本为 21 场，另有 3 场验证。")
        self.assertIn("FACT_NUMBER_ADDED", codes(result))

    def test_unit_change_fails_without_duplicate_noise(self) -> None:
        result = run_check("RMSE 为 8.78 mm。", "RMSE 为 8.78 cm。")
        found = codes(result)
        self.assertIn("FACT_UNIT_CHANGED", found)
        self.assertNotIn("FACT_NUMBER_MISSING", found)
        self.assertNotIn("FACT_NUMBER_ADDED", found)
        self.assertNotIn("FACT_NUMBER_ORDER", found)

    def test_citation_missing_fails(self) -> None:
        result = run_check(r"已有研究\cite{a,b}支持。", r"已有研究\cite{a}支持。")
        self.assertIn("FACT_CITATION_MISSING", codes(result))

    def test_direction_flip_fails(self) -> None:
        result = run_check("该方法精度提升。", "该方法精度下降。")
        self.assertIn("FACT_DIRECTION_FLIPPED", codes(result))

    def test_reordered_numbers_warn(self) -> None:
        result = run_check("分别为 1 mm 和 2 mm。", "分别为 2 mm 和 1 mm。")
        self.assertEqual(result["verdict"], "WARN")
        self.assertIn("FACT_NUMBER_ORDER", codes(result))

    def test_protected_term_missing_fails(self) -> None:
        result = run_check("采用 KAN-PC 模型。", "采用代理模型。", terms="KAN-PC")
        self.assertIn("FACT_TERM_MISSING", codes(result))

    def test_percent_unit_is_preserved(self) -> None:
        result = run_check("精度提升 5%。", "精度提升 5%。")
        self.assertEqual(result["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
