#!/usr/bin/env python3
"""获取章节模板骨架，可选注入 {{占位符}} 参数。

对应原 MCP 工具 fill_section_template_tool。模板位于 skill 的
assets/profiles/<paper_type>/sections_{zh,en}.md 与 assets/templates/。
"""

from __future__ import annotations

import argparse

import _common as C

TOOL = "fill_section_template"


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="获取论文章节、投稿信或审稿回复模板。",
        epilog="退出码：0 成功；2 参数或输入错误；3 模板缺失/不可读。",
    )
    parser.add_argument("--section", required=True, help="章节名，如 abstract、method、introduction_en、cover_letter")
    parser.add_argument("--params", default="{}", help='{{占位符}} 的 JSON 对象字符串，默认 "{}"')
    parser.add_argument("--params-file", help="从 UTF-8 JSON 文件读取 params（优先于 --params）")
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--paper-type", default="general", help="general / method-experiment / case-study / review")
    parser.add_argument("--profile", default="", help="项目 Profile，如 songbei-urban-flood")
    return parser


def run(args: argparse.Namespace) -> dict:
    params = args.params
    if args.params_file:
        params = C.read_text(None, args.params_file, "params")

    base_key = args.section.lower()
    selected_language = "en" if base_key.endswith("_en") else args.language
    key = base_key if base_key.endswith("_en") else (
        f"{base_key}_en" if selected_language == "en" else base_key
    )

    if key not in C.SECTION_MAP and key not in C.EXTRA_SECTIONS:
        available = ", ".join(sorted(set(C.SECTION_MAP) | set(C.EXTRA_SECTIONS)))
        raise C.UsageError(f"未知章节 '{args.section}'。可用章节：{available}")

    if key in C.EXTRA_SECTIONS:
        filename, language = C.EXTRA_SECTIONS[key]
        path = C.TEMPLATE_DIR / filename
        try:
            template = path.read_text(encoding="utf-8")
        except Exception as exc:
            raise C.ToolRuntimeError(f"读取模板文件失败：{exc}") from exc
        rendered, error = C.render_template_params(template, params)
        if error:
            raise C.UsageError(error)
        return {
            "section": args.section,
            "language": language,
            "paper_type": args.paper_type,
            "profile": args.profile,
            "template_id": "extra",
            "evidence_basis": C.PROFILE_EVIDENCE["extra"],
            "template": rendered,
        }

    template_id = C.resolve_template_id(args.paper_type, args.profile)
    section_title = C.SECTION_MAP[key]
    if template_id in C.PROFILE_SECTION_TITLES:
        profile_key = base_key.removesuffix("_en")
        titles = C.PROFILE_SECTION_TITLES[template_id][selected_language]
        if profile_key not in titles:
            raise C.UsageError(
                f"profile '{template_id}' 不包含章节 '{profile_key}'"
                f"（该 profile 可用章节：{', '.join(sorted(titles))}）"
            )
        section_title = titles[profile_key]

    path = C.template_path(template_id, selected_language)
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise C.ToolRuntimeError(f"读取模板文件失败：{exc}") from exc

    lines = content.split("\n")
    result = []
    in_target = False
    section_depth = 0
    for line in lines:
        if line.strip().startswith(f"## {section_title}"):
            in_target = True
            section_depth = line.count("#")
            result.append(line)
            continue
        if in_target:
            if line.startswith("#") and line.count("#") <= section_depth:
                break
            result.append(line)

    rendered, error = C.render_template_params("\n".join(result).strip(), params)
    if error:
        raise C.UsageError(error)
    return {
        "section": args.section,
        "language": selected_language,
        "paper_type": args.paper_type,
        "profile": args.profile,
        "template_id": template_id,
        "evidence_basis": C.PROFILE_EVIDENCE[template_id],
        "template": rendered,
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
