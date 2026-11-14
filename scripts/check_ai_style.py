#!/usr/bin/env python3
"""AI 写作风格的结构化检测：模板腔、节奏均质、证据密度、连接词堆叠、知网句式。

与 check_academic_language.py 的分工：
- 后者查词表（局部用词）；
- 本脚本查段落/句群结构（模板化、无具体信息、节奏过匀），并输出三层：
  FAIL = 结构性模板腔；WARN = 可疑写作习惯；INFO = 个性化风格提示。
知网句式（动宾+了、A的B与C、形容词+名词重复、长句）来自公开视频的个人实测，
是经验规则而非官方口径。
"""

from __future__ import annotations

import argparse
import html
import re
import statistics
from collections import Counter
from pathlib import Path

import _common as C

TOOL = "check_ai_style"

ORDINAL_PREFIXES = ("首先", "其次", "再次", "最后", "第一", "第二", "第三", "其一", "其二", "一方面", "另一方面")
TRANSITIONS = ("此外", "因此", "然而", "同时", "进一步", "综上所述", "值得注意的是", "具体而言", "总之", "换言之")
AI_WORDS = (
    "值得注意的是", "综上所述", "具体而言", "赋能", "闭环", "协同", "范式",
    "全面提升", "显著提升", "深度赋能", "底层逻辑", "抓手", "痛点",
)
VO_PATTERN = re.compile(
    r"(?:研究|发现|提出|明确|揭示|梳理|界定|对比分析|论证|给出|构建|设计|"
    r"采用|验证|分析|总结|阐述|探讨|评估|优化|改进|实现|建立|形成|划分|"
    r"识别|提取|计算|模拟|预测|比较|讨论|说明|证明|表明)了"
)
NOUN_CHAIN_PATTERN = re.compile(
    r"[\u4e00-\u9fff]{2,8}的[\u4e00-\u9fff]{2,8}(?:与|和)[\u4e00-\u9fff]{2,8}"
)
ADJ_NOUN_PATTERN = (
    "重要意义", "重要作用", "核心特征", "关键问题", "主要方法", "显著提升",
    "有效手段", "重要价值", "理论基础", "实践意义", "突出贡献", "明显优势",
)
LONG_SENTENCE_CHARS = 80


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
    parser.add_argument("--report", help="输出自包含 HTML 段落骨架报告到该路径")
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


def split_sentences(text: str, language: str = "zh") -> list[str]:
    if language == "en":
        parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    else:
        parts = re.split(r"[。！？!?；;\n]+", text)
    return [item.strip() for item in parts if len(item.strip()) >= 2]


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


REPORT_CSS = """
body{font-family:-apple-system,"Segoe UI","Noto Sans CJK SC",sans-serif;margin:24px;color:#1f2933;background:#fbfbfd;line-height:1.5}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:24px 0 8px}
.muted{color:#6b7785;font-size:12px}
.verdict{display:inline-block;padding:3px 10px;border-radius:12px;color:#fff;font-size:12px;font-weight:600}
.PASS{background:#2f9e6e}.WARN{background:#c98a1b}.FAIL{background:#c94a4a}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:12px 0}
.metric{background:#fff;border:1px solid #e4e7eb;border-radius:6px;padding:8px 10px}
.metric b{display:block;font-size:16px;margin-top:2px}
table{border-collapse:collapse;width:100%;background:#fff;margin-top:6px}
th,td{border-bottom:1px solid #e4e7eb;padding:6px 8px;text-align:left;font-size:13px;vertical-align:top}
th{background:#f1f4f8;font-weight:600}
tr.hit{background:#fff4e0}
.bar{height:10px;background:#4c9ac9;border-radius:2px;min-width:2px}
.cell{display:inline-block;min-width:20px;text-align:center;border-radius:2px;margin:1px;font-size:11px;padding:1px 2px}
.s{background:#e8f3fb}.m{background:#b9dcf2}.l{background:#7fb8dd;color:#fff}
.issue{border-left:4px solid #c98a1b;background:#fff;padding:8px 12px;margin:6px 0}
.issue.FAIL{border-left-color:#c94a4a}.issue.INFO{border-left-color:#6b7785}
.code{font-family:Consolas,monospace;font-size:12px;color:#4c5a68}
.suggestion{color:#2f4f6f;font-size:12px;margin-top:4px}
"""


def _paragraph_rows(text: str) -> tuple[list[dict], set[int]]:
    language = "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"
    paragraphs = split_paragraphs(text) or [text.strip()]
    rows = []
    for index, paragraph in enumerate(paragraphs, 1):
        sentences = split_sentences(paragraph, language)
        rows.append(
            {
                "index": index,
                "opening": paragraph[:18],
                "sentences": len(sentences),
                "chars": len(paragraph),
                "lengths": [len(item) for item in sentences],
                "ordinal": paragraph.startswith(ORDINAL_PREFIXES),
                "specific": is_specific(paragraph),
            }
        )

    hit_rows: set[int] = set()
    run: list[int] = []
    for position, row in enumerate(rows):
        if row["ordinal"] and position > 0 and abs(row["sentences"] - rows[position - 1]["sentences"]) <= 1:
            run.append(position)
        elif row["ordinal"]:
            run = [position]
        else:
            run = []
        if len(run) >= 3:
            hit_rows.update(run)
    return rows, hit_rows


def build_report(text: str, data: dict, output_path: str) -> Path:
    """Write a self-contained HTML report of paragraph skeletons."""
    rows, hit_rows = _paragraph_rows(text)
    metrics = data.get("metrics", {})
    max_sentences = max((row["sentences"] for row in rows), default=1) or 1
    max_chars = max((row["chars"] for row in rows), default=1) or 1

    parts = [
        "<!doctype html><html lang='zh'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>段落骨架报告</title><style>",
        REPORT_CSS,
        "</style></head><body>",
        "<h1>段落骨架报告</h1>",
        f"<span class='verdict {html.escape(data.get('verdict', 'PASS'))}'>"
        f"{html.escape(data.get('verdict', 'PASS'))}</span>",
        f"<div class='muted'>段落 {html.escape(str(metrics.get('paragraphs', len(rows))))} · "
        f"句数 {html.escape(str(metrics.get('sentences', 0)))} · "
        f"句长 CV {html.escape(str(metrics.get('sentence_length_cv', 0)))} · "
        f"低证据段占比 {html.escape(str(metrics.get('low_specificity_ratio', 0)))}</div>",
        "<div class='metrics'>",
    ]
    for label, key in (
        ("段落", "paragraphs"),
        ("句数", "sentences"),
        ("句长 CV", "sentence_length_cv"),
        ("低证据占比", "low_specificity_ratio"),
        ("序数段", "ordinal_paragraphs"),
        ("连接词开头占比", "transition_ratio"),
        ("AI 词/千字", "ai_word_density_per_1000"),
        ("知网动宾+了", "vo_le_total"),
        ("名词串", "noun_chains"),
        ("长句", "long_sentences"),
    ):
        parts.append(
            f"<div class='metric'>{html.escape(label)}<b>{html.escape(str(metrics.get(key, 0)))}</b></div>"
        )
    parts.append("</div>")

    parts.append("<h2>段落骨架</h2>")
    parts.append("<table><thead><tr><th>#</th><th>段首</th><th>句数</th><th>字数</th>"
                 "<th>句数占比</th><th>特征</th></tr></thead><tbody>")
    for position, row in enumerate(rows):
        width = max(2, round(row["sentences"] / max_sentences * 100))
        marks = []
        if row["ordinal"]:
            marks.append("序数开头")
        if not row["specific"]:
            marks.append("无具体信息")
        if position in hit_rows:
            marks.append("模板网格")
        row_class = " class='hit'" if position in hit_rows else ""
        parts.append(
            f"<tr{row_class}><td>{row['index']}</td><td>{html.escape(row['opening'])}</td>"
            f"<td>{row['sentences']}</td><td>{row['chars']}</td>"
            f"<td><div class='bar' style='width:{width}%'></div></td>"
            f"<td>{html.escape('、'.join(marks) or '—')}</td></tr>"
        )
    parts.append("</tbody></table>")

    parts.append("<h2>句长网格</h2>")
    parts.append("<div class='muted'>每格为一句的字数；颜色越深表示句子越长。</div>")
    parts.append("<table><thead><tr><th>#</th>")
    for column in range(1, min(max_sentences, 12) + 1):
        parts.append(f"<th>S{column}</th>")
    parts.append("</tr></thead><tbody>")
    for position, row in enumerate(rows):
        row_class = " class='hit'" if position in hit_rows else ""
        parts.append(f"<tr{row_class}><td>{row['index']}</td>")
        for column in range(min(max_sentences, 12)):
            if column < len(row["lengths"]):
                length = row["lengths"][column]
                tone = "s" if length < 15 else ("m" if length <= 35 else "l")
                parts.append(f"<td><span class='cell {tone}'>{length}</span></td>")
            else:
                parts.append("<td>—</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")

    parts.append("<h2>问题清单</h2>")
    issues = data.get("issues", [])
    if not issues:
        parts.append("<p class='muted'>没有命中规则。</p>")
    for issue in issues:
        severity = html.escape(issue.get("severity", "INFO"))
        parts.append(f"<div class='issue {severity}'>")
        parts.append(
            f"<b>{severity}</b> <span class='code'>{html.escape(issue.get('code', ''))}</span> "
            f"{html.escape(issue.get('message', ''))}"
        )
        for example in issue.get("examples", [])[:3]:
            parts.append(f"<div class='muted'>· {html.escape(str(example)[:180])}</div>")
        if issue.get("suggestion"):
            parts.append(f"<div class='suggestion'>{html.escape(issue['suggestion'])}</div>")
        parts.append("</div>")

    parts.append(
        "<p class='muted' style='margin-top:24px'>结构检测只提示模板化与信息密度，"
        "不判断文本是否由 AI 生成；知网句式为经验规则、非官方口径。</p>"
    )
    parts.append("</body></html>")

    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")
    return path


def run(args: argparse.Namespace) -> dict:
    text = C.read_text(args.text, args.input_file)
    if not text.strip():
        raise C.UsageError("text 不能为空")
    lang = C.detect_language(text, args.language)

    paragraphs = split_paragraphs(text)
    sentences = split_sentences(text, lang)
    if not paragraphs:
        paragraphs = [text.strip()]
    sentence_lengths = [len(item) for item in sentences]
    paragraph_sentence_counts = [len(split_sentences(item, lang)) for item in paragraphs]
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

    if len(sentences) >= 5 and sentence_cv and sentence_cv < 0.22:
        issues.append(
            {
                "severity": "WARN",
                "code": "AI_UNIFORM_RHYTHM",
                "message": f"句长变异系数 {sentence_cv:.2f}（<0.22），节奏过于均匀",
                "examples": [f"句数 {len(sentences)}，平均 {statistics.mean(sentence_lengths):.1f} 字"],
            }
        )

    if len(paragraphs) >= 3 and specificity_ratio > 0.5:
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

    # 知网 2026-10 更新后常见的两类句式（经验规则，非官方口径）。
    vo_hot = []
    vo_total = 0
    for paragraph in paragraphs:
        hits = VO_PATTERN.findall(paragraph)
        vo_total += len(hits)
        sentence_counts = [len(VO_PATTERN.findall(item)) for item in split_sentences(paragraph, lang)]
        max_in_sentence = max(sentence_counts) if sentence_counts else 0
        if len(hits) >= 6 or max_in_sentence >= 3:
            vo_hot.append((paragraph, len(hits), max_in_sentence))
    if lang == "zh" and vo_hot:
        issues.append(
            {
                "severity": "WARN",
                "code": "CNKI_VO_PILE",
                "message": f"动宾+“了”句式扎堆（{sum(item[1] for item in vo_hot)} 处，涉及 {len(vo_hot)} 段）",
                "examples": [f"{item[0][:80]}（{item[1]} 处，单句最多 {item[2]}）" for item in vo_hot[:3]],
                "suggestion": "换语序而不是删内容：'梳理了X'→'对X进行梳理'，'明确了Y'→'将Y明确'；保留专业表述。",
            }
        )

    noun_hot = []
    for paragraph in paragraphs:
        hits = [match.group(0) for match in NOUN_CHAIN_PATTERN.finditer(paragraph)]
        if len(hits) >= 2:
            noun_hot.append((paragraph, hits))
    noun_chains = [chain for _, hits in noun_hot for chain in hits]
    if lang == "zh" and noun_hot:
        issues.append(
            {
                "severity": "WARN",
                "code": "CNKI_NOUN_CHAIN",
                "message": f"同一段出现 ≥2 处 A的B与C 型名词串（{len(noun_hot)} 段）",
                "examples": [
                    f"{paragraph[:70]}（{'、'.join(dict.fromkeys(hits))}）"
                    for paragraph, hits in noun_hot[:3]
                ],
                "suggestion": "拆开名词串：'A的B与C'→'A的B；C...'；'X的两大特征'→'X的特征有两个：...'。",
            }
        )

    repeated_adj_noun = [
        f"{word}×{text.count(word)}"
        for word in ADJ_NOUN_PATTERN
        if text.count(word) >= 2
    ]
    adj_counts = {word: text.count(word) for word in ADJ_NOUN_PATTERN}
    if lang == "zh" and (any(count >= 3 for count in adj_counts.values()) or len(repeated_adj_noun) >= 3):
        issues.append(
            {
                "severity": "WARN",
                "code": "CNKI_ADJ_NOUN_REPEAT",
                "message": f"形容词+名词组合重复（{len(repeated_adj_noun)} 组）",
                "examples": repeated_adj_noun[:6],
                "suggestion": "拆散重复组合，换成具体对象、条件或数据，不要只换同义词。",
            }
        )

    long_sentences = [item for item in sentences if len(item) > LONG_SENTENCE_CHARS]
    long_ratio = len(long_sentences) / len(sentences) if sentences else 0.0
    if lang == "zh" and len(sentences) >= 5 and len(long_sentences) >= 2 and long_ratio >= 0.2:
        issues.append(
            {
                "severity": "WARN",
                "code": "CNKI_LONG_SENTENCE",
                "message": f"{len(long_sentences)}/{len(sentences)} 句超过 {LONG_SENTENCE_CHARS} 字（{long_ratio:.0%}）",
                "examples": [item[:100] for item in long_sentences[:2]],
                "suggestion": "长句拆短、短句合并，避免整段句长与结构过于均匀。",
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
            "vo_le_total": vo_total,
            "noun_chains": len(noun_chains),
            "repeated_adj_noun": len(repeated_adj_noun),
            "long_sentences": len(long_sentences),
        },
        "issues": issues,
        "note": "结构检测只提示模板化与信息密度，不判断是否由 AI 生成；知网句式规则为经验规则、非官方口径，最终以人工读稿与学校指定平台复检为准。",
    }


def main(argv: list[str] | None = None) -> int:
    C.configure_stdio()
    args = build_parser().parse_args(argv)
    try:
        data = run(args)
        if args.report:
            text = C.read_text(args.text, args.input_file)
            report_path = build_report(text, data, args.report)
            data["report_path"] = str(report_path)
    except C.UsageError as exc:
        return C.emit_error(TOOL, str(exc), 2)
    except C.ToolRuntimeError as exc:
        return C.emit_error(TOOL, str(exc), 3)
    return C.emit(TOOL, data, 1 if data["verdict"] == "FAIL" else 0)


if __name__ == "__main__":
    raise SystemExit(main())
