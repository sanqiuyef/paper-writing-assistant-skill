#!/usr/bin/env python3
"""检查文本中的 AI 标记词，返回命中位置与语料级替换建议。

对应原 MCP 工具 check_academic_language_tool。子串匹配、词典顺序与语言
判定均沿用原实现，便于与 MCP 版本逐项对照。
"""

from __future__ import annotations

import argparse
import re

import _common as C

TOOL = "check_academic_language"


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="检查中英文文本中的 AI 标记词，返回命中位置与替换建议。",
        epilog="退出码：0 成功；2 参数或输入错误；3 运行时错误。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="待检查文本")
    group.add_argument("--input-file", help="UTF-8 文本文件路径；- 表示从 stdin 读取")
    parser.add_argument("--language", choices=["auto", "zh", "en"], default="auto")
    return parser


def run(args: argparse.Namespace) -> dict:
    text = C.read_text(args.text, args.input_file)
    lang = C.detect_language(text, args.language)
    db = C.load_lexicon()
    word_db = db.get("zh_words" if lang == "zh" else "en_words", {})
    text_lower = text.lower()

    findings = []
    for pattern, replacement in word_db.items():
        if pattern in text_lower:
            for match in re.finditer(re.escape(pattern), text, flags=re.IGNORECASE):
                start = max(0, match.start() - 20)
                end = min(len(text), match.start() + len(pattern) + 20)
                context = text[start:end].replace("\n", " ").strip()
                findings.append(
                    {
                        "pattern": pattern,
                        "suggested_replacement": replacement,
                        "context": f"...{context}...",
                        "position": match.start(),
                    }
                )

    if not findings:
        return {
            "status": "clean",
            "message": f"未检测到常见 AI 标记词（{len(findings)} 处）",
            "language": lang,
            "findings": [],
        }
    return {
        "status": "issues_found",
        "message": f"检测到 {len(findings)} 处可能的 AI 标记词",
        "language": lang,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    C.configure_stdio()
    args = build_parser().parse_args(argv)
    try:
        return C.emit(TOOL, run(args))
    except C.UsageError as exc:
        return C.emit_error(TOOL, str(exc), 2)
    except C.ToolRuntimeError as exc:
        return C.emit_error(TOOL, str(exc), 3)


if __name__ == "__main__":
    raise SystemExit(main())
