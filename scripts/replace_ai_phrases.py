#!/usr/bin/env python3
"""检测 AI 腔用词并给出替换建议；--apply 时以 [[建议]] 占位符执行替换。

对应原 MCP 工具 replace_ai_phrases_tool。默认 dry-run，不改原文。
"""

from __future__ import annotations

import argparse
import re

import _common as C

TOOL = "replace_ai_phrases"


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="检测 AI 腔用词并给出学术表达建议；默认只报不改。",
        epilog="退出码：0 成功；2 参数或输入错误；3 运行时错误。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="待处理文本")
    group.add_argument("--input-file", help="UTF-8 文本文件路径；- 表示从 stdin 读取")
    parser.add_argument("--language", choices=["auto", "zh", "en"], default="auto")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="执行替换，把命中词替换为 [[建议核心词]] 占位符（默认 False 仅报建议）",
    )
    return parser


def run(args: argparse.Namespace) -> dict:
    text = C.read_text(args.text, args.input_file)
    lang = C.detect_language(text, args.language)
    db = C.load_lexicon()
    word_db = db.get("zh_words" if lang == "zh" else "en_words", {})

    result_text = text
    details = []
    for pattern, replacement in word_db.items():
        if pattern in result_text.lower():
            core = re.sub(r"[（）()]", "", replacement).strip() if replacement else ""
            if not core:
                continue
            count = len(re.findall(re.escape(pattern), result_text.lower()))
            if args.apply:
                result_text = re.sub(
                    re.escape(pattern), f"[[{core}]]", result_text, flags=re.IGNORECASE
                )
            details.append(
                {
                    "pattern": pattern,
                    "replaced_with": core.strip("（").strip("）").strip(),
                    "count": count,
                }
            )

    return {
        "original_length": len(text),
        "replacements_made": len(details),
        "applied": args.apply,
        "details": details,
        "result_text": result_text,
        "note": (
            "已按 --apply 执行替换，[[建议]] 为待人工确认的占位符。"
            if args.apply
            else "未修改原文（dry-run）。请按 details 中的建议人工改写；"
            "如确需自动替换请加 --apply。"
        ),
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
