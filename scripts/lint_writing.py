#!/usr/bin/env python3
"""确定性写作质量门控：AI 指纹、句式、载体纯净度，返回 PASS/WARN/FAIL。

对应原 MCP 工具 lint_writing_tool；规则引擎为 scripts/writing_lint.py。
退出码：0 = PASS/WARN（检查完成），1 = FAIL（门控不通过），2 = 参数错误，3 = 运行时错误。
"""

from __future__ import annotations

import argparse

import _common as C
import writing_lint

TOOL = "lint_writing"
MODES = ("plain", "word", "docx", "markdown", "latex")


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="确定性写作质量门控（AI 指纹/句式/载体纯净度）。",
        epilog="退出码：0 PASS/WARN；1 FAIL；2 参数错误；3 运行时错误。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="待检查文本")
    group.add_argument("--input-file", help="UTF-8 文本文件路径；- 表示从 stdin 读取")
    parser.add_argument("--mode", choices=MODES, default="plain")
    parser.add_argument("--language", choices=["auto", "zh", "en"], default="auto")
    return parser


def run(args: argparse.Namespace) -> dict:
    text = C.read_text(args.text, args.input_file)
    if not text.strip():
        raise C.UsageError("text 不能为空")
    lang = C.detect_language(text, args.language)
    issues = writing_lint.lint_text(text, mode=args.mode, lang=lang)
    summary = writing_lint.summarize(issues)
    return {
        "verdict": summary["verdict"],
        "fail": summary["fail"],
        "warn": summary["warn"],
        "info": summary["info"],
        "mode": args.mode,
        "language": lang,
        "issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "line": issue.line,
                "count": issue.count,
                "message": issue.message,
                "examples": issue.examples,
            }
            for issue in issues
        ],
        "note": "FAIL 项必须修复后复检；WARN 项评估后决定是否回改；INFO 项仅提示。退出码 1 表示 FAIL，不是执行失败。",
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
