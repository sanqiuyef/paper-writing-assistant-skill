#!/usr/bin/env python3
"""DeepSeek 降 AI 味改写：返回改写稿、改动说明与数字编造风险。

对应原 MCP 工具 rewrite_academic_text_tool。语料来源优先级：
--kb-dir / PWA_KB_DIR > Obsidian vault > 旧快照；证据级检索请先用
lancedb-search MCP，把命中段落经 --reference-file 传入。
"""

from __future__ import annotations

import argparse

import _common as C
import _rewrite

TOOL = "rewrite_academic_text"


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="调用 DeepSeek 降低文本 AI 味，保留事实、数值与引用。",
        epilog="退出码：0 成功；2 参数或输入错误；3 缺少 API key、语料无命中或调用失败。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="待改写文本")
    group.add_argument("--input-file", help="UTF-8 文本文件路径；- 表示从 stdin 读取")
    parser.add_argument("--style", default="mixed", help="academic / official-media / mixed（默认）")
    parser.add_argument("--language", choices=["auto", "zh", "en"], default="auto")
    parser.add_argument("--reference-texts", default="", help="范文片段，仅模仿句式与节奏")
    parser.add_argument("--reference-file", help="从 UTF-8 文件读取范文片段（与 --reference-texts 合并）")
    parser.add_argument("--corpus", default="", help="领域范文集：songbei / cross-domain / official-media")
    parser.add_argument("--paper-type", default="general", help="general / method-experiment / case-study / review")
    parser.add_argument("--corpus-sections", default="", help="逗号分隔的章节过滤")
    parser.add_argument("--profile", default="", help="项目背景说明")
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--kb", default="", help="语料检索范围：空=全库，zh/en=语言，或主题目录名")
    parser.add_argument("--kb-dir", default="", help="显式指定语料根目录（默认 Obsidian vault）")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只组装提示词与范文，不调用 DeepSeek；由宿主 agent 自行改写（零外部请求）",
    )
    return parser


def run(args: argparse.Namespace) -> dict:
    text = C.read_text(args.text, args.input_file)
    reference = args.reference_texts or ""
    if args.reference_file:
        extra = C.read_text(None, args.reference_file, "reference")
        reference = (reference + "\n\n" + extra).strip() if reference else extra
    if args.dry_run:
        prepared = _rewrite.prepare(
            text=text,
            style=args.style,
            language=args.language,
            reference_texts=reference,
            corpus=args.corpus,
            paper_type=args.paper_type,
            corpus_sections=args.corpus_sections,
            profile=args.profile,
            kb=args.kb,
            kb_dir=args.kb_dir or None,
        )
        prepared["dry_run"] = True
        prepared["note"] = "未发起网络请求。把 system_prompt/user_prompt 交给宿主 agent 改写，再按 risks 核对数字。"
        return prepared
    return _rewrite.rewrite(
        text=text,
        style=args.style,
        language=args.language,
        reference_texts=reference,
        corpus=args.corpus,
        paper_type=args.paper_type,
        corpus_sections=args.corpus_sections,
        profile=args.profile,
        temperature=args.temperature,
        kb=args.kb,
        kb_dir=args.kb_dir or None,
    )


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
