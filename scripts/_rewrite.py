"""DeepSeek-backed academic rewrite used by rewrite_academic_text.py.

Prompt assembly and the numeric-fabrication guard follow the MCP server
implementations (2026-11). Robustness fixes made during the script migration:
- ``requests`` is imported lazily so lint/latex scripts never need it;
- a non-object model JSON or a non-JSON HTTP body yields a clear runtime error
  instead of an uncaught AttributeError / JSONDecodeError.
"""

from __future__ import annotations

import json
import os
import re

import _kb
from _common import (
    STYLE_ALIASES,
    ToolRuntimeError,
    UsageError,
    flag_new_numbers,
    load_config,
    load_lexicon,
    load_style_guide,
)

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


def _deepseek_config() -> dict:
    value = load_config().get("deepseek")
    return value if isinstance(value, dict) else {}


def _endpoint() -> str:
    return os.environ.get("DEEPSEEK_API_URL") or _deepseek_config().get(
        "endpoint", DEEPSEEK_API_URL
    )


def _model_name() -> str:
    return os.environ.get("DEEPSEEK_MODEL") or _deepseek_config().get(
        "model", "deepseek-chat"
    )


def _timeout() -> int:
    raw = os.environ.get("DEEPSEEK_TIMEOUT")
    if raw is None:
        raw = str(_deepseek_config().get("timeout", 120))
    try:
        return int(raw)
    except ValueError as exc:
        raise ToolRuntimeError(f"DEEPSEEK_TIMEOUT 必须是整数，当前为 {raw!r}") from exc


def build_system_prompt(
    style: str,
    reference_texts: str,
    language: str,
    corpus_texts: str = "",
    kb_texts: str = "",
) -> str:
    parts = [
        "你是资深学术写作编辑，任务是降低文本的\"AI 味\"、还原自然的学术笔触，"
        "同时严格保留原文的事实、数据、结论与引用。",
    ]
    guide = load_style_guide(style)
    if guide:
        parts.append(f"\n[风格指引 —— 必须遵守]\n{guide}")

    db = load_lexicon()
    if language == "zh":
        blocklist = db.get("zh_words", {})
    elif language == "en":
        blocklist = db.get("en_words", {})
    else:
        blocklist = {}
    if blocklist:
        lines = []
        for word, hint in blocklist.items():
            if word in ("从...到...再到...", "从……到……再到……"):
                continue
            lines.append(f"- \"{word}\"：{hint}")
        if lines:
            parts.append(
                "\n[AI 腔黑名单 —— 原文出现下列表达时必须改写，禁止原样保留]\n"
                + "\n".join(lines)
            )

    if reference_texts:
        parts.append(
            "\n[范文参考 —— 来自真实学术文献/官媒语料]\n"
            "只模仿这些片段的句式、过渡方式与论证节奏，禁止复制其内容、数据或引用：\n"
            f"{reference_texts[:6000]}"
        )
    if corpus_texts:
        parts.append(
            "\n[范文参考 —— 来自领域精选文献范文集（按章节分类）]\n"
            "模仿这些片段的句式、术语运用与论证节奏，禁止复制其内容、数据或引用：\n"
            f"{corpus_texts[:6000]}"
        )
    if kb_texts:
        parts.append(
            "\n[范文参考 —— 来自本地 Markdown 语料库关键词检索（与原文主题相关）]\n"
            "模仿这些片段的句式、过渡方式与论证节奏，禁止复制其内容、数据或引用。"
            "片段源自 PDF 文本层，可能混有公式线性化残骸（符号错位、分式拍平）与页眉页脚水印，"
            "忽略这些排布伪影，不模仿其数学符号串：\n"
            f"{kb_texts[:6000]}"
        )
    parts.append(
        "\n[硬性要求]\n"
        "1. 输出必须是合法 JSON，包含四个字段：rewritten（改写后全文）、"
        "changes（改动说明数组，每项含 type/original/revised/reason）、"
        "preserved_facts（确认保留的事实）、risks（可能的语义偏移，无则空数组）。\n"
        "2. 不得改动或新增数字、单位、专有名词、引用标记和结论本身。"
        "严禁编造原文没有的数据、指标、百分比、速度或数值；原文没有具体数字就保留模糊表述或如实留白。\n"
        "3. 只输出 JSON，不要输出任何额外文字。"
    )
    return "\n".join(parts)


def call_deepseek(system_prompt: str, user_text: str, temperature: float) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ToolRuntimeError(
            "未设置 DEEPSEEK_API_KEY 环境变量，无法调用 DeepSeek 改写。"
            "请在运行脚本的终端中设置该变量后重试。"
        )
    try:
        import requests
    except ImportError as exc:  # pragma: no cover
        raise ToolRuntimeError("缺少 requests 依赖，无法调用 DeepSeek") from exc

    payload = {
        "model": _model_name(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": temperature,
        "stream": False,
    }
    try:
        response = requests.post(
            _endpoint(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json=payload,
            timeout=_timeout(),
        )
        response.raise_for_status()
    except Exception as exc:
        raise ToolRuntimeError(f"DeepSeek 调用失败：{exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise ToolRuntimeError(
            f"DeepSeek 返回非 JSON 响应（前 500 字符）：{response.text[:500]}"
        ) from exc
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ToolRuntimeError(f"DeepSeek 返回格式异常：{str(data)[:500]}") from exc


def extract_json_object(raw: str) -> dict:
    """Extract a JSON object, tolerating ```json fences and surrounding prose."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    candidates = [text]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
        raise ToolRuntimeError(
            "模型输出是合法 JSON 但不是对象（应为 rewritten/changes/... 结构）"
            f"：{str(value)[:300]}"
        )
    raise ToolRuntimeError(f"模型输出不是合法 JSON：{raw[:500]}")


def rewrite(
    text: str,
    style: str = "mixed",
    language: str = "auto",
    reference_texts: str = "",
    corpus: str = "",
    paper_type: str = "general",
    corpus_sections: str = "",
    profile: str = "",
    temperature: float = 0.3,
    kb: str = "",
    kb_dir: str | None = None,
    corpus_loader=None,
) -> dict:
    """Run one rewrite and return the model object plus provenance flags."""
    if not text.strip():
        raise UsageError("text 不能为空")
    if language not in {"auto", "zh", "en"}:
        raise UsageError("language 必须是 'auto'、'zh' 或 'en'")

    normalized_style = STYLE_ALIASES.get(style.strip().lower(), style.strip().lower())
    if language == "auto":
        lang = "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"
    else:
        lang = language

    corpus_texts = ""
    if corpus:
        if corpus_loader is None:
            from _common import load_corpus_examples

            corpus_loader = load_corpus_examples
        corpus_texts = corpus_loader(corpus, paper_type, corpus_sections)
        if not corpus_texts:
            raise ToolRuntimeError(
                f"corpus '{corpus}' / paper_type '{paper_type}' 下没有可用范文"
            )

    kb_texts = ""
    if kb:
        kb_texts = _kb.search(text[:2000], kb, kb_dir=kb_dir)
        if not kb_texts:
            raise ToolRuntimeError(
                f"kb '{kb}' 检索失败（kb 名无效或语料库中无相关片段）"
            )

    system_prompt = build_system_prompt(
        normalized_style, reference_texts, lang, corpus_texts, kb_texts
    )
    user_prompt = (
        f"语言：{lang}\n待改写文本：\n{text}"
        + (f"\n\n项目背景：{profile}" if profile else "")
    )

    raw = call_deepseek(system_prompt, user_prompt, temperature)
    result = extract_json_object(raw)
    result.setdefault("style", normalized_style)
    result.setdefault("language", lang)
    result.setdefault("reference_texts_used", bool(reference_texts))
    result.setdefault("corpus_examples_used", bool(corpus_texts))
    result.setdefault("kb_used", bool(kb_texts))

    rewritten = result.get("rewritten") or ""
    if isinstance(rewritten, str) and rewritten:
        fabricated = flag_new_numbers(text, rewritten)
        if fabricated:
            result["risks"] = (result.get("risks") or []) + [
                "检测到改写稿出现原文没有的数值，请务必核实是否为模型编造："
                + "、".join(fabricated)
            ]
    return result
