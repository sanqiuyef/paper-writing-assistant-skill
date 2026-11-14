"""Structural AI-style checks: template grids, rhythm, specificity, word density."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_ai_style as style  # noqa: E402


def run_check(text: str) -> dict:
    return style.run(argparse.Namespace(text=text, input_file=None, language="auto"))


def codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"]}


TEMPLATE = """首先，城市内涝预报具有重要价值。其次，现有方法存在不足。最后，本文提出新方法。

首先，数据来源需要说明。其次，模型结构需要介绍。最后，实验结果需要讨论。

首先，精度指标需要比较。其次，区间覆盖需要分析。最后，计算成本需要评估。
"""

NATURAL = """本文在松北区21场降雨上测试，RMSE 为 8.78 mm，PICP 为 0.8465。与 ConvLSTM 相比，KAN-PC 的误差降低 33%，但高重现期仍有欠覆盖。已有研究报告了类似趋势，说明样本量仍是主要限制。

计算成本方面，代理模型单场推理 52.4 ms，求解器为 2.226 s。该差异来自网络前向替代了迭代求解，而不是精度换速度。
"""


class AiStyleTest(unittest.TestCase):
    def test_template_grid_fails(self) -> None:
        result = run_check(TEMPLATE)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("AI_TEMPLATE_GRID", codes(result))

    def test_natural_text_passes(self) -> None:
        result = run_check(NATURAL)
        self.assertEqual(result["verdict"], "PASS")
        self.assertLess(result["metrics"]["low_specificity_ratio"], 0.5)

    def test_uniform_rhythm_warns(self) -> None:
        text = "城市内涝预报需要更快的模型。现有物理模型计算耗时较长。代理模型可以缩短推理时间。"
        result = run_check(text)
        self.assertIn("AI_UNIFORM_RHYTHM", codes(result))

    def test_low_specificity_warns(self) -> None:
        text = "城市内涝预报具有重要价值。现有方法仍存在一定不足。本文提出了一种新的思路。"
        result = run_check(text)
        self.assertIn("AI_LOW_SPECIFICITY", codes(result))

    def test_ai_words_are_info_only(self) -> None:
        result = run_check("值得注意的是，赋能与闭环需要具体对象，否则只是空话。")
        density = [issue for issue in result["issues"] if issue["code"] == "AI_WORD_DENSITY"]
        self.assertTrue(density)
        self.assertEqual(density[0]["severity"], "INFO")
        self.assertNotEqual(result["verdict"], "FAIL")

    def test_markdown_headings_not_counted_as_paragraphs(self) -> None:
        text = "# 标题\n\n## 小节\n\n正文段落包含 21 场降雨与 8.78 mm 的 RMSE，长度足够进入统计。"
        result = run_check(text)
        self.assertEqual(result["metrics"]["paragraphs"], 1)


if __name__ == "__main__":
    unittest.main()
