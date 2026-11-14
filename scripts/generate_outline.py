#!/usr/bin/env python3
"""生成论文写作大纲（章节结构 + 配图方案）。

对应原 MCP 工具 generate_outline_tool。读取
assets/profiles/<paper_type>/outline_{zh,en}.json。
"""

from __future__ import annotations

import argparse
import json

import _common as C

TOOL = "generate_outline"


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="生成论文写作大纲，支持 paper_type 与项目 profile。",
        epilog="退出码：0 成功；2 参数错误；3 大纲文件缺失或不可读。",
    )
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--paper-type", default="general", help="general / method-experiment / case-study / review")
    parser.add_argument("--profile", default="", help="项目 Profile，如 songbei-urban-flood")
    return parser


def run(args: argparse.Namespace) -> dict:
    template_id = C.resolve_template_id(args.paper_type, args.profile)
    path = C.outline_path(template_id, args.language)
    try:
        outline = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise C.ToolRuntimeError(f"读取大纲配置失败：{exc}") from exc

    # 与原实现一致：paper_type 输出解析后的 template_id，profile 原样回显。
    outline["paper_type"] = template_id
    outline["profile"] = args.profile
    outline["template_id"] = template_id
    outline["evidence_basis"] = C.PROFILE_EVIDENCE[template_id]
    outline["available_paper_types"] = sorted(C.PAPER_TYPES)
    outline["available_profiles"] = sorted(C.PROJECT_PROFILES)
    return outline


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
