#!/usr/bin/env python3
"""AI 写作风格的结构化检测：模板腔、节奏均质、证据密度、连接词堆叠。

与 check_academic_language.py 的分工：
- 后者查词表（局部用词）；
- 本脚本查段落/句群结构（模板化、无具体信息、节奏过匀），并输出三层：
  FAIL = 结构性模板腔；WARN = 可疑写作习惯；INFO = 个性化风格提示。
"""

from __future__ import annotations

import argparse
import re
import statistics
from collections import Counter

import _common as C

TOOL = "check_ai_style"

ORDINAL_PREFIXES = ("首先", "其次", "再次", "最后", "第一", "第二", "第三", "其一", "其二", "一方面", "另一方面")
TRANSITIONS = ("此外", "因此", "然而", "同时", "进一步", "综上所述", "值得注意的是", "具体而言", "总之", "换言之")
AI_WORDS = (
    "值得注意的是", "综上所述", "具体而言", "赋能", "闭环", "协同", "范式",
    "全面提升", "显著提升", "深度赋能", "底层逻辑", "抓手", "痛点",
)


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="检测 AI 写作风格的结构特征（模板腔、节奏、证据密度）。",
        epilog="退出码：0 PASS/WARN；1 FAIL；2 参数或输入错误；3 运行时错误。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="待检查文本")
    group.add_argument("--input-file", help="UTF-8 文本文件路径；- 表示从 stdin 读取")
    parser.add_argument("--language", choices=["auto", "zh", "en"], default="auto")
    return parser


def split_paragraphs(text: str) -> list[str]:
    paragraphs = []
    for item in re.split(r"\n\s*\n", text):
        paragraph = item.strip()
        if len(paragraph) < 20:
            continue
        if paragraph.startswith(("#", "|", "**", ">", "- ")):
            continue
        paragraphs.append(paragraph)
    return paragraphs


def split_sentences(text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[。！？!?；;\n]+", text)
        if len(item.strip()) >= 2
    ]


def coefficient_of_variation(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    return statistics.pstdev(values) / mean if mean else 0.0


def is_specific(paragraph: str) -> bool:
    return bool(
        re.search(r"\d", paragraph)
        or re.search(r"\[\d+", paragraph)
        or re.search(r"\\cite", paragraph)
        or re.search(r"[A-Za-z][A-Za-z0-9_-]{2,}", paragraph)
        or "《" in paragraph
    )


def run(args: argparse.Namespace) -> dict:
    text = C.read_text(args.text, args.input_file)
    if not text.strip():
        raise C.UsageError("text 不能为空")
    lang = C.detect_language(text, args.language)

    paragraphs = split_paragraphs(text)
    sentences = split_sentences(text)
    if not paragraphs:
        paragraphs = [text.strip()]
    sentence_lengths = [len(item) for item in sentences]
    paragraph_sentence_counts = [len(split_sentences(item)) for item in paragraphs]
    sentence_cv = coefficient_of_variation(sentence_lengths)
    paragraph_cv = coefficient_of_variation(paragraph_sentence_counts)

    ordinal_paragraphs = [
        index for index, item in enumerate(paragraphs) if item.startswith(ORDINAL_PREFIXES)
    ]
    low_specificity = [index for index, item in enumerate(paragraphs) if not is_specific(item)]
    specificity_ratio = len(low_specificity) / len(paragraphs) if paragraphs else 0.0

    transition_sentences = [
        item for item in sentences if item.startswith(TRANSITIONS)
    ]
    transition_ratio = len(transition_sentences) / len(sentences) if sentences else 0.0

    opening_prefixes = [item[:6] for item in paragraphs]
    repeated_openings = [
        prefix for prefix, count in Counter(opening_prefixes).items() if count >= 3
    ]

    ai_word_hits = sum(text.count(word) for word in AI_WORDS)
    ai_word_density = ai_word_hits / max(1, len(text)) * 1000

    issues = []

    # FAIL：连续 3 段用序数开头且句数高度一致，属于可识别的模板骨架。
    grid_run = 0
    grid_hit = False
    for index, paragraph in enumerate(paragraphs):
        if paragraph.startswith(ORDINAL_PREFIXES):
            if index > 0 and abs(paragraph_sentence_counts[index] - paragraph_sentence_counts[index - 1]) <= 1:
                grid_run += 1
            else:
                grid_run = 1
            if grid_run >= 3:
                grid_hit = True
                break
        else:
            grid_run = 0
    if grid_hit:
        issues.append(
            {
                "severity": "FAIL",
                "code": "AI_TEMPLATE_GRID",
                "message": "连续 3 段使用序数开头且句数高度一致，呈提纲模板骨架",
                "examples": [paragraphs[index][:80] for index in ordinal_paragraphs[:3]],
            }
        )

    if sentence_cv and sentence_cv < 0.22:
        issues.append(
            {
                "severity": "WARN",
                "code": "AI_UNIFORM_RHYTHM",
                "message": f"句长变异系数 {sentence_cv:.2f}（<0.22），节奏过于均匀",
                "examples": [f"句数 {len(sentences)}，平均 {statistics.mean(sentence_lengths):.1f} 字" if sentence_lengths else ""],
            }
        )

    if specificity_ratio > 0.5:
        issues.append(
            {
                "severity": "WARN",
                "code": "AI_LOW_SPECIFICITY",
                "message": f"{len(low_specificity)}/{len(paragraphs)} 段没有数字、引用、术语或文献名，抽象度过高",
                "examples": [paragraphs[index][:80] for index in low_specificity[:3]],
            }
        )

    if len(ordinal_paragraphs) >= 3:
        issues.append(
            {
                "severity": "WARN",
                "code": "AI_ORDINAL_OPENINGS",
                "message": f"{len(ordinal_paragraphs)} 段以“首先/其次/最后”类序数开头",
                "examples": [paragraphs[index][:80] for index in ordinal_paragraphs[:3]],
            }
        )

    if repeated_openings:
        issues.append(
            {
                "severity": "INFO",
                "code": "AI_REPEATED_OPENINGS",
                "message": f"{len(repeated_openings)} 个段首前缀重复出现 ≥3 次（风格提示）",
                "examples": repeated_openings[:5],
            }
        )

    if transition_ratio > 0.4:
        issues.append(
            {
                "severity": "WARN",
                "code": "AI_TRANSITION_DENSITY",
                "message": f"{transition_ratio:.0%} 的句子以固定连接词开头",
                "examples": [item[:60] for item in transition_sentences[:3]],
            }
        )

    if ai_word_density > 3:
        issues.append(
            {
                "severity": "INFO",
                "code": "AI_WORD_DENSITY",
                "message": f"AI 高频词密度 {ai_word_density:.1f}/千字（仅风格提示）",
                "examples": [word for word in AI_WORDS if word in text][:8],
            }
        )

    fail = sum(1 for item in issues if item["severity"] == "FAIL")
    warn = sum(1 for item in issues if item["severity"] == "WARN")
    info = sum(1 for item in issues if item["severity"] == "INFO")
    verdict = "FAIL" if fail else ("WARN" if warn else "PASS")
    return {
        "verdict": verdict,
        "fail": fail,
        "warn": warn,
        "info": info,
        "language": lang,
        "metrics": {
            "chars": len(text),
            "paragraphs": len(paragraphs),
            "sentences": len(sentences),
            "sentence_length_cv": round(sentence_cv, 3),
            "paragraph_sentence_cv": round(paragraph_cv, 3),
            "low_specificity_ratio": round(specificity_ratio, 3),
            "ordinal_paragraphs": len(ordinal_paragraphs),
            "transition_ratio": round(transition_ratio, 3),
            "ai_word_density_per_1000": round(ai_word_density, 2),
        },
        "issues": issues,
        "note": "结构检测只提示模板化与信息密度，不判断是否由 AI 生成；最终以人工读稿为准。",
    }


def main(argv: list[str] | None = None) -> int:
    C.configure_stdio()
    args = build_parser().parse_args(argv)
    try:
        data = run(args)
    except C.UsageError as exc:
        return C.emit_error(TOOL, str(exc), 2)
    except C.ToolRuntimeError as exc:
        return C.emit_error(TOOL, str(exc), 3)
    return C.emit(TOOL, data, 1 if data["verdict"] == "FAIL" else 0)


if __name__ == "__main__":
    raise SystemExit(main())
