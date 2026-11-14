#!/usr/bin/env python3
"""扫描论文中的防御性写作，返回可逐条修改的问题清单。

规则与 ``references/anti_defensive_writing.md`` 同一口径：自贬、否定式叠甲、
预演质疑、过程汇报、括号摊底、第一人称、叠层模糊、边界重复，以及删防御后
可能出现的反向夸大。检测器只报不改；真实边界是否保留由作者判断。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import _common as C

TOOL = "check_defensive_writing"
PATTERNS_PATH = Path(__file__).resolve().parent / "defensive_patterns.json"
SECTIONS = ("body", "abstract", "introduction", "results", "discussion", "conclusion")
SEVERITY_ORDER = {"FAIL": 0, "WARN": 1, "INFO": 2}


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="扫描防御性写作并给出逐条修改建议。",
        epilog="退出码：0 PASS/WARN；1 FAIL；2 参数或输入错误；3 规则文件缺失或非法。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="待检查文本")
    group.add_argument("--input-file", help="UTF-8 文本文件路径；- 表示从 stdin 读取")
    parser.add_argument("--section", choices=SECTIONS, default="body", help="章节位置；摘要/结论会额外检查开头")
    parser.add_argument("--strict", action="store_true", help="把 WARN 提升为 FAIL（用于终稿门控）")
    return parser


def load_patterns() -> dict:
    try:
        data = json.loads(PATTERNS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise C.ToolRuntimeError(f"读取防御性规则失败：{PATTERNS_PATH}（{exc}）") from exc
    if not isinstance(data, dict) or not isinstance(data.get("categories"), list):
        raise C.ToolRuntimeError("defensive_patterns.json 结构非法")
    return data


def split_sentences(text: str):
    """Yield (sentence, start_offset) on Chinese/English sentence boundaries."""
    for match in re.finditer(r"[^。！？!?；;\n]+[。！？!?；;]?", text):
        sentence = match.group(0).strip()
        if sentence:
            yield sentence, match.start()


def line_of(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def context(text: str, start: int, end: int, width: int = 30) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return text[left:right].replace("\n", " ").strip()


def _is_negated_overclaim(text: str, position: int) -> bool:
    """Skip overclaim hits that sit inside an explicit negation."""
    prefix = text[max(0, position - 12):position]
    return any(word in prefix for word in ("不存在", "并非", "不是", "没有", "不能", "未"))


def collect_category_issues(text: str, categories: list) -> list:
    issues = []
    for category in categories:
        severity = category.get("severity", "WARN")
        compiled = []
        for pattern in category.get("patterns", []):
            try:
                compiled.append(re.compile(pattern))
            except re.error as exc:
                raise C.ToolRuntimeError(
                    f"规则 {category.get('code')} 的正则非法：{pattern}（{exc}）"
                ) from exc
        matches = []
        for regex in compiled:
            matches.extend(regex.finditer(text))
        if category.get("code") == "DEF_OVERCLAIM":
            matches = [
                match for match in matches if not _is_negated_overclaim(text, match.start())
            ]
        if not matches:
            continue
        matches.sort(key=lambda item: item.start())
        issues.append(
            {
                "severity": severity,
                "code": category.get("code", "DEF"),
                "line": line_of(text, matches[0].start()),
                "count": len(matches),
                "message": f"{category.get('message', '防御性表达')}（{category.get('name', '')}）",
                "examples": [
                    context(text, match.start(), match.end()) for match in matches[:3]
                ],
                "suggestion": category.get("suggestion", ""),
            }
        )
    return issues


def collect_hedge_issue(text: str, rule: dict) -> list:
    terms = rule.get("terms") or []
    warn_at = int(rule.get("warn_at", 2))
    fail_at = int(rule.get("fail_at", 3))
    hits = []
    for sentence, position in split_sentences(text):
        present = [term for term in terms if term in sentence]
        if len(present) >= warn_at:
            hits.append(
                {
                    "severity": "FAIL" if len(present) >= fail_at else "WARN",
                    "position": position,
                    "terms": present,
                    "sentence": sentence,
                }
            )
    if not hits:
        return []
    severity = "FAIL" if any(hit["severity"] == "FAIL" for hit in hits) else "WARN"
    return [
        {
            "severity": severity,
            "code": rule.get("code", "DEF_HEDGE_STACK"),
            "line": line_of(text, hits[0]["position"]),
            "count": len(hits),
            "message": f"{rule.get('message', '叠层模糊限定')}（{'/'.join(hits[0]['terms'])}）",
            "examples": [hit["sentence"][:120] for hit in hits[:3]],
            "suggestion": rule.get("suggestion", ""),
        }
    ]


def collect_density_issues(text: str, rules: list) -> list:
    issues = []
    for rule in rules:
        try:
            matches = list(re.finditer(rule["pattern"], text))
        except re.error as exc:
            raise C.ToolRuntimeError(
                f"规则 {rule.get('code')} 的正则非法：{rule['pattern']}（{exc}）"
            ) from exc
        count = len(matches)
        if count < int(rule.get("warn_at", 3)):
            continue
        severity = "FAIL" if count >= int(rule.get("fail_at", 6)) else rule.get("severity", "WARN")
        issues.append(
            {
                "severity": severity,
                "code": rule.get("code", "DEF_BOUNDARY_REPEAT"),
                "line": line_of(text, matches[0].start()),
                "count": count,
                "message": f"{rule.get('message', '边界声明重复')}（{count} 处）",
                "examples": [
                    context(text, match.start(), match.end()) for match in matches[:3]
                ],
                "suggestion": rule.get("suggestion", ""),
            }
        )
    return issues


def collect_opening_issue(text: str, section: str, data: dict, categories: list) -> list:
    rule = data.get("section_rule") or {}
    if section not in (rule.get("sections") or []):
        return []
    first_n = int(rule.get("first_sentences", 3))
    opening = list(split_sentences(text))[:first_n]
    if not opening:
        return []
    fail_categories = [item for item in categories if item.get("severity") == "FAIL"]
    hit_sentence = ""
    for sentence, _ in opening:
        for category in fail_categories:
            if any(re.search(pattern, sentence) for pattern in category.get("patterns", [])):
                hit_sentence = sentence
                break
        if hit_sentence:
            break
    if not hit_sentence:
        return []
    return [
        {
            "severity": rule.get("severity", "FAIL"),
            "code": rule.get("code", "DEF_OPENING_DEPRECATION"),
            "line": 1,
            "count": 1,
            "message": rule.get("message", "摘要/结论开头出现自我削弱"),
            "examples": [hit_sentence[:120]],
            "suggestion": rule.get("suggestion", ""),
        }
    ]


def run(args: argparse.Namespace) -> dict:
    text = C.read_text(args.text, args.input_file)
    if not text.strip():
        raise C.UsageError("text 不能为空")
    data = load_patterns()
    categories = data["categories"]

    issues = []
    issues.extend(collect_category_issues(text, categories))
    issues.extend(collect_hedge_issue(text, data.get("hedge_rule") or {}))
    issues.extend(collect_density_issues(text, data.get("density_rules") or []))
    issues.extend(collect_opening_issue(text, args.section, data, categories))

    if args.strict:
        for issue in issues:
            if issue["severity"] == "WARN":
                issue["severity"] = "FAIL"

    issues.sort(key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), item["line"]))
    fail = sum(1 for item in issues if item["severity"] == "FAIL")
    warn = sum(1 for item in issues if item["severity"] == "WARN")
    info = sum(1 for item in issues if item["severity"] == "INFO")
    verdict = "FAIL" if fail else ("WARN" if warn else "PASS")
    return {
        "verdict": verdict,
        "fail": fail,
        "warn": warn,
        "info": info,
        "section": args.section,
        "chars": len(text),
        "issues": issues,
        "note": "检测器只报不改。真实边界保留一次并正面表述；删除防御不得反向夸大主张。",
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
