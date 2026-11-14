#!/usr/bin/env python3
"""LaTeX 转义体检；--fix 返回转义修复稿（数学环境原样保留）。

对应原 MCP 工具 latex_sanitize_tool；规则引擎为 scripts/latex_clean.py。
退出码：0 = 无 FAIL 级问题，1 = 存在 FAIL 级问题，2 = 参数错误，3 = 运行时错误。
"""

from __future__ import annotations

import argparse

import _common as C
import latex_clean

TOOL = "latex_sanitize"


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="LaTeX 转义体检与可选修复。",
        epilog="退出码：0 无 FAIL；1 存在 FAIL 级问题；2 参数错误；3 运行时错误。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="待检查的 LaTeX 片段")
    group.add_argument("--input-file", help="UTF-8 文件路径；- 表示从 stdin 读取")
    parser.add_argument("--fix", action="store_true", help="返回自动转义修复稿（数学环境保留）")
    return parser


def run(args: argparse.Namespace) -> dict:
    text = C.read_text(args.text, args.input_file)
    if not text.strip():
        raise C.UsageError("text 不能为空")

    problems = [
        {"severity": severity, "message": message}
        for severity, message in latex_clean.check_latex(text)
    ]
    result = {
        "problem_count": len(problems),
        "problems": problems,
        "note": "建议正文中写 \\% \\& \\# \\_；命令参数（如 \\cite{a_b}）内的下划线通常无害。",
    }
    if args.fix:
        fixed = latex_clean.escape_latex(text)
        result["fixed_text"] = fixed
        result["changed"] = fixed != text
    return result


def main(argv: list[str] | None = None) -> int:
    C.configure_stdio()
    args = build_parser().parse_args(argv)
    try:
        data = run(args)
    except C.UsageError as exc:
        return C.emit_error(TOOL, str(exc), 2)
    except C.ToolRuntimeError as exc:
        return C.emit_error(TOOL, str(exc), 3)
    has_fail = any(item["severity"] == "FAIL" for item in data["problems"])
    return C.emit(TOOL, data, 1 if has_fail else 0)


if __name__ == "__main__":
    raise SystemExit(main())
