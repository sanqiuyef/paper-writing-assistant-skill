"""Shared constants and helpers for paper-writing-assistant scripts.

All scripts live in ``scripts/`` and resolve data relative to the skill root,
so the skill is self-contained and does not import the MCP server at runtime.
Original behaviour follows mcp_servers/paper-writing-assistant/mcp_server/server.py
(2026-11 版本)；本文件只做路径重定位与 CLI 适配。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSETS_DIR = SKILL_DIR / "assets"
TEMPLATE_DIR = SKILL_DIR / "templates"
PROFILE_DIR = ASSETS_DIR / "profiles"
STYLE_DIR = ASSETS_DIR / "styles"
CORPUS_DIR = (
    ASSETS_DIR / "corpus"
    if (ASSETS_DIR / "corpus").is_dir()
    else ASSETS_DIR / "corpus.example"
)
KB_DIR = ASSETS_DIR / "knowledge_base"
CONFIG_PATH = SKILL_DIR / "config" / "defaults.json"
LEXICON_PATH = SCRIPT_DIR / "_lexicon.json"

_CONFIG_CACHE: dict | None = None


def load_config() -> dict:
    """Load config/defaults.json once; a missing file degrades to empty defaults."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        try:
            value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            _CONFIG_CACHE = value if isinstance(value, dict) else {}
        except Exception:
            _CONFIG_CACHE = {}
    return _CONFIG_CACHE

CORPUS_NAMES = {
    "songbei": "songbei",
    "cross-domain": "cross-domain",
    "crossdomain": "cross-domain",
    "跨学科": "cross-domain",
    "official-media": "official-media",
    "官媒": "official-media",
}
CORPUS_SECTIONS = {"introduction", "method", "experiment", "discussion"}

PAPER_TYPES = {"general", "method-experiment", "case-study", "review"}
PROJECT_PROFILES = {"songbei-urban-flood"}
PROFILE_ALIASES = {
    "method": "method-experiment",
    "experiment": "method-experiment",
    "case": "case-study",
    "systematic-review": "review",
    "songbei": "songbei-urban-flood",
    "songbei-flood": "songbei-urban-flood",
}

PROFILE_EVIDENCE = {
    "general": "通用 IMRaD 与中文期刊常见结构的保守交集",
    "method-experiment": "本地知识库中的城市洪涝代理模型、图神经网络和深度学习方法论文",
    "case-study": "本地知识库中的 IFMS、SWMM-SIMWE、CAflood 等区域案例研究",
    "review": "本地知识库中的系统综述、方法综述和研究进展论文",
    "songbei-urban-flood": "项目专用数据基准与本地城市洪涝期刊文献（示例 profile 不随仓库分发）",
    "extra": "scipilot-writing-skill v1.0.0 投稿信/审稿回复剧本（MIT License，已融合改编）",
}

SECTION_MAP = {
    "abstract": "1. 摘要",
    "introduction": "2. 引言",
    "related_work": "3. 相关研究",
    "method": "4. 研究方法",
    "experiment": "5. 实验设计",
    "result": "6. 结果与分析",
    "discussion": "7. 讨论",
    "conclusion": "8. 结论",
    "abstract_en": "1. Abstract",
    "introduction_en": "2. Introduction",
    "related_work_en": "3. Related Work",
    "method_en": "4. Methodology",
    "experiment_en": "5. Experimental Design",
    "result_en": "6. Results and Analysis",
    "discussion_en": "7. Discussion",
    "conclusion_en": "8. Conclusion",
}

EXTRA_SECTIONS = {
    "cover_letter": ("cover_letter_zh.md", "zh"),
    "cover_letter_en": ("cover_letter_en.md", "en"),
    "rebuttal": ("rebuttal_zh.md", "zh"),
    "rebuttal_en": ("rebuttal_en.md", "en"),
}

PROFILE_SECTION_TITLES = {
    "songbei-urban-flood": {
        "zh": {
            "abstract": "1. 摘要",
            "introduction": "2. 引言",
            "method": "4. 模型与方法",
            "experiment": "5. 实验设计",
            "result": "6. 结果与分析",
            "discussion": "7. 讨论",
            "conclusion": "8. 结论",
        },
        "en": {
            "abstract": "1. Abstract",
            "introduction": "2. Introduction",
            "method": "4. Methodology",
            "experiment": "5. Experimental Design",
            "result": "6. Results",
            "discussion": "7. Discussion",
            "conclusion": "8. Conclusions",
        },
    },
}

STYLE_ALIASES = {
    "academic": "academic",
    "文献": "academic",
    "学术": "academic",
    "official-media": "official-media",
    "official_media": "official-media",
    "官媒": "official-media",
    "人民日报": "official-media",
    "mixed": "mixed",
    "混合": "mixed",
}


class JsonArgumentParser(argparse.ArgumentParser):
    """Argparse that keeps the stdout-JSON contract on usage errors."""

    tool = "paper-writing-assistant"

    def error(self, message: str):  # type: ignore[override]
        self.print_usage(sys.stderr)
        payload = {"ok": False, "tool": self.tool, "error": message}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(2)


def json_parser(tool: str, **kwargs) -> JsonArgumentParser:
    parser = JsonArgumentParser(**kwargs)
    parser.tool = tool
    return parser


class UsageError(ValueError):
    """Bad arguments or invalid input data (CLI exit code 2)."""


class ToolRuntimeError(RuntimeError):
    """Missing asset, unreadable template, or failed external call (exit code 3)."""


def configure_stdio() -> None:
    """Force UTF-8 on Windows consoles and pipes."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def emit(tool: str, data: Any, exit_code: int = 0) -> int:
    """Print one JSON object to stdout and return the process exit code."""
    payload = {"ok": True, "tool": tool, "data": data}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


def emit_error(tool: str, message: str, exit_code: int) -> int:
    payload = {"ok": False, "tool": tool, "error": message}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


def read_text(text: str | None, input_file: str | None, label: str = "text") -> str:
    """Resolve text from --text, --input-file PATH, or --input-file - (stdin)."""
    if text is not None:
        return text
    if input_file == "-":
        raw = sys.stdin.buffer.read()
        for encoding in ("utf-8", "gbk"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UsageError("stdin 内容既不是 UTF-8 也不是 GBK，请改用 --input-file")
    if not input_file:
        raise UsageError(f"{label} 不能为空：请传 --text 或 --input-file")
    path = Path(input_file)
    if not path.is_file():
        raise UsageError(f"输入文件不存在：{path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise UsageError(f"输入文件不是 UTF-8：{path}（{exc}）") from exc


def detect_language(text: str, language: str = "auto") -> str:
    """Validate zh/en/auto and return the concrete language."""
    if language not in {"auto", "zh", "en"}:
        raise UsageError("language 必须是 'auto'、'zh' 或 'en'")
    if language == "auto":
        return "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"
    return language


def load_lexicon() -> dict:
    """Load the 45 zh + 78 en replacement entries extracted from the MCP server."""
    try:
        return json.loads(LEXICON_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - asset missing is a install error
        raise ToolRuntimeError(f"读取词库失败：{LEXICON_PATH}（{exc}）") from exc


def normalize_profile_name(value: str) -> str:
    normalized = (value or "").strip().lower().replace("_", "-")
    return PROFILE_ALIASES.get(normalized, normalized)


def resolve_template_id(paper_type: str, profile: str) -> str:
    selected_type = normalize_profile_name(paper_type or "general")
    if selected_type not in PAPER_TYPES:
        raise UsageError(f"paper_type 必须是 {', '.join(sorted(PAPER_TYPES))} 之一")

    selected_profile = normalize_profile_name(profile)
    if selected_profile:
        if selected_profile not in PROJECT_PROFILES:
            raise UsageError(
                f"未知 profile '{profile}'。可用项目 Profile："
                f"{', '.join(sorted(PROJECT_PROFILES))}"
            )
        return selected_profile
    return selected_type


def template_path(template_id: str, language: str) -> Path:
    filename = "sections_zh.md" if language == "zh" else "sections_en.md"
    return PROFILE_DIR / template_id / filename


def outline_path(template_id: str, language: str) -> Path:
    filename = "outline_zh.json" if language == "zh" else "outline_en.json"
    return PROFILE_DIR / template_id / filename


def render_template_params(template: str, params: str) -> tuple[str, str | None]:
    """Apply explicit {{name}} placeholders without interpreting arbitrary text."""
    if not params or params == "{}":
        return template, None
    try:
        values = json.loads(params)
    except json.JSONDecodeError as exc:
        return template, f"params must be a JSON object: {exc.msg}"
    if not isinstance(values, dict):
        return template, "params must be a JSON object"
    for key, value in values.items():
        if not isinstance(key, str):
            return template, "params keys must be strings"
        template = template.replace("{{" + key + "}}", str(value))
    return template, None


def load_corpus_examples(corpus: str, paper_type: str, sections: str = "") -> str:
    """Load selected example paragraphs from assets/corpus/<corpus>/<paper_type>.json."""
    if corpus not in CORPUS_NAMES:
        return ""
    path = CORPUS_DIR / CORPUS_NAMES[corpus] / f"{paper_type}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""

    wanted = {s.strip() for s in sections.split(",") if s.strip()} if sections else None
    blocks = []
    for section, examples in (data.get("sections") or {}).items():
        if wanted and section not in wanted:
            continue
        for ex in examples or []:
            text = (ex.get("text") or "").strip()
            if not text:
                continue
            blocks.append(f"[{section} · {ex.get('source', '')}]\n{text}")
    return "\n\n".join(blocks)


def load_style_guide(style: str) -> str:
    """Read a style guide; a missing file degrades to an empty guide."""
    try:
        return (STYLE_DIR / f"{style}.md").read_text(encoding="utf-8")
    except Exception:
        return ""


# Unit suffix used to spot numeric claims; citations/years are handled separately.
NUM_UNIT = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|％|°|℃|km|m|cm|mm|s|h|min|ms|GB|MB|FPS|Hz|dB|Pa|kPa|MPa|m³|m2|km²|人|万|亿|元|m/s|km/h)\b"
)
NUM_BARE = re.compile(r"\b\d{1,3}(?:\.\d+)?\b")


def extract_numeric_tokens(text: str) -> set[str]:
    """Extract numbers with units plus bare numbers, excluding 1900-2099 years."""
    tokens: set[str] = set()
    for match in NUM_UNIT.finditer(text):
        tokens.add(match.group(0).strip())
    for match in NUM_BARE.finditer(text):
        value = match.group(0)
        if 1900 <= int(float(value)) <= 2099:
            continue
        tokens.add(value)
    return tokens


def flag_new_numbers(original: str, rewritten: str) -> list[str]:
    """Numbers present in the rewrite but absent from the source (possible fabrication)."""
    original_tokens = extract_numeric_tokens(original)
    return [tok for tok in sorted(extract_numeric_tokens(rewritten)) if tok not in original_tokens]
