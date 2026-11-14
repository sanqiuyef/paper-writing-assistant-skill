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
        text = (
            "城市内涝预报需要更快的模型。现有物理模型计算耗时较长。"
            "代理模型可以缩短推理时间。网络前向替代了迭代求解。"
            "该差异来自结构而不是精度换速度。"
        )
        result = run_check(text)
        self.assertIn("AI_UNIFORM_RHYTHM", codes(result))

    def test_low_specificity_warns(self) -> None:
        text = (
            "城市内涝预报具有重要价值。现有方法仍存在一定不足。本文提出了一种新的思路。\n\n"
            "该方法关注整体流程。它强调结构上的改进。结果需要进一步讨论。\n\n"
            "未来工作可以继续完善。也可以扩展到更多场景。还需要更多实验支持。"
        )
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

    def test_cnki_vo_pile(self) -> None:
        text = "本章梳理了概念，界定了范围，对比分析了已有方法，论证了可行性，给出了结论。"
        result = run_check(text)
        self.assertIn("CNKI_VO_PILE", codes(result))

    def test_cnki_noun_chain(self) -> None:
        text = (
            "本章梳理了灾后应急物流的概念内涵与场景特点，界定了研究对象。"
            "该模型的核心优势与适用范围仍需讨论。"
        )
        result = run_check(text)
        self.assertIn("CNKI_NOUN_CHAIN", codes(result))

    def test_cnki_adj_noun_repeat(self) -> None:
        text = "该工作具有重要意义。该指标具有重要意义。该结论同样具有重要意义。"
        result = run_check(text)
        self.assertIn("CNKI_ADJ_NOUN_REPEAT", codes(result))

    def test_cnki_long_sentences(self) -> None:
        long_sentence = (
            "本文在松北区二十一场降雨与多个重现期情景上对代理模型的误差和区间覆盖率"
            "进行了系统比较并讨论了其在不同降雨强度下的变化趋势与适用范围以及计算成本"
            "与部署限制" * 2 + "。"
        )
        text = long_sentence + "\n\n" + long_sentence + "\n\n短句一。短句二。短句三。"
        result = run_check(text)
        self.assertIn("CNKI_LONG_SENTENCE", codes(result))

    def test_english_sentence_split(self) -> None:
        result = run_check(
            "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        )
        self.assertEqual(result["metrics"]["sentences"], 5)

    def test_html_report(self) -> None:
        import tempfile

        result = run_check(TEMPLATE)
        with tempfile.TemporaryDirectory() as temp:
            path = style.build_report(TEMPLATE, result, str(Path(temp) / "report.html"))
            content = path.read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", content)
        self.assertIn("段落骨架", content)
        self.assertIn("句长网格", content)
        self.assertIn("AI_TEMPLATE_GRID", content)


if __name__ == "__main__":
    unittest.main()
