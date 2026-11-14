"""Local Markdown knowledge-base search used by rewrite_academic_text.

Corpus sources, in priority order:
1. ``--kb-dir`` / ``PWA_KB_DIR`` (explicit path);
2. ``vault_dir`` in ``config/defaults.json`` or ``PWA_VAULT_DIR``;
3. ``assets/knowledge_base`` only if a legacy snapshot exists in the skill.

For evidence-grade retrieval the agent should call the ``lancedb-search`` MCP
(``search_knowledge``/``get_document``) first and pass the returned passages via
``--reference-file``. This module is the offline fallback and keeps the original
paragraph-scoring behaviour of the MCP server.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from _common import KB_DIR, ToolRuntimeError, load_config

VAULT_DIR = Path(os.environ["PWA_VAULT_DIR"]) if os.environ.get("PWA_VAULT_DIR") else None
EXCLUDE_PARTS = {
    ".git", ".obsidian", ".trash", ".zcode", ".tmp-video-frames", ".video_agent",
    "06-templates-模板", "05-journal-日记与周记",
}

KB_LEGACY_NAMES = {
    "songbei", "小论文", "academic-writing", "学术写作语料",
    "cross-domain", "official-media", "官媒", "all",
}
KB_STOPWORDS_ZH = {
    "的", "了", "和", "与", "及", "对", "在", "是", "为", "以", "于", "等", "并",
    "或", "其", "之", "上", "下", "中", "基于", "研究", "方法", "分析", "结果", "本文",
}
KB_STOPWORDS_EN = {
    "the", "and", "for", "with", "based", "using", "from", "that", "this", "study",
    "method", "results", "analysis", "approach", "paper", "research", "propose", "proposed",
}
KB_PARA_NOISE = (
    "学号", "密级", "单位代码", "学校代码", "分类号：", "指导教师", "论文提交日期",
    "评阅人", "论文作者签名", "原创性声明", "dissertation submitted",
    "in partial fulfillment", "downloaded from", "downloaded via",
    "this article is protected",
)
_CACHE: dict = {}


def _iter_md(root: Path):
    for md in sorted(root.rglob("*.md")):
        parts = md.relative_to(root).parts
        if any(part.startswith(".") or part in EXCLUDE_PARTS for part in parts):
            continue
        yield md


def _dir_signature(root: Path) -> tuple:
    latest = 0.0
    count = 0
    for md in _iter_md(root):
        count += 1
        mtime = md.stat().st_mtime
        if mtime > latest:
            latest = mtime
    return (count, latest)


def _strip_frontmatter(raw: str) -> str:
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            return raw[end + 4:]
    return raw


def load_paragraphs(root: Path) -> list:
    signature = _dir_signature(root)
    cached = _CACHE.get(str(root))
    if cached and cached[0] == signature:
        return cached[1]
    docs = []
    for md in _iter_md(root):
        try:
            raw = md.read_text(encoding="utf-8")
        except OSError:
            continue
        body = _strip_frontmatter(raw)
        paras = [
            p.strip()
            for p in re.split(r"\n\s*\n", body)
            if len(p.strip()) >= 40 and not any(noise in p for noise in KB_PARA_NOISE)
        ]
        if paras:
            docs.append((md.relative_to(root).as_posix(), paras))
    _CACHE[str(root)] = (signature, docs)
    return docs


def extract_terms(query: str, max_terms: int = 32) -> list[tuple[str, float]]:
    cleaned = query[:2000]
    for word in KB_STOPWORDS_ZH:
        cleaned = cleaned.replace(word, " ")
    terms: list[str] = []

    def add(term: str) -> None:
        if term and term not in terms and len(terms) < max_terms:
            terms.append(term)

    for run in re.findall(r"[\u4e00-\u9fff]{2,}", cleaned):
        if len(run) <= 4:
            add(run)
        else:
            windows = [run[i:i + 4] for i in range(0, len(run) - 3, 2)]
            if len(windows) > 6:
                idx = [round(i * (len(windows) - 1) / 5) for i in range(6)]
                windows = [windows[i] for i in dict.fromkeys(idx)]
            for window in windows:
                add(window)
    for token in re.findall(r"[A-Za-z][A-Za-z-]{2,}", query[:2000]):
        term = token.lower().strip("-")
        if len(term) >= 3 and term not in KB_STOPWORDS_EN:
            add(term)
    return [
        (t, float(len(t) ** 2) if re.search(r"[\u4e00-\u9fff]", t) else float(len(t)))
        for t in terms
    ]


def resolve_root(kb_dir: str | None = None) -> Path:
    """Resolve the corpus root: explicit path > PWA_KB_DIR > vault > legacy snapshot."""
    if kb_dir:
        return Path(kb_dir).expanduser().resolve()
    env = os.environ.get("PWA_KB_DIR")
    if env:
        return Path(env).expanduser().resolve()
    configured = load_config().get("vault_dir")
    if configured and Path(configured).is_dir():
        return Path(configured).expanduser().resolve()
    if VAULT_DIR and VAULT_DIR.is_dir():
        return VAULT_DIR
    if KB_DIR.is_dir():
        return KB_DIR
    raise ToolRuntimeError(
        "未找到可用语料目录：请用 --kb-dir 指定，或设置 PWA_KB_DIR / PWA_VAULT_DIR"
    )


def search(query: str, kb: str = "", limit: int = 4, kb_dir: str | None = None) -> str:
    """Search the configured corpus. ``kb`` is a scope name (zh/en/topic), not a path."""
    root = resolve_root(kb_dir)
    lang_scope = ""
    if kb and kb not in KB_LEGACY_NAMES:
        if kb in ("zh", "en"):
            lang_scope = kb
        elif (root / kb).is_dir():
            root = root / kb
        else:
            return ""
    if not root.is_dir():
        raise ToolRuntimeError(f"知识库目录不存在：{root}")

    docs = load_paragraphs(root)
    if not docs:
        return ""
    terms = extract_terms(query)
    if not terms:
        return ""

    scored = []
    for rel, paras in docs:
        for para in paras:
            if lang_scope == "zh" and not re.search(r"[\u4e00-\u9fff]", para):
                continue
            if lang_scope == "en" and re.search(r"[\u4e00-\u9fff]", para):
                continue
            score = 0.0
            for term, weight in terms:
                count = para.count(term)
                if count:
                    score += count * weight
            if score > 0:
                scored.append((score, rel, para))
    if not scored:
        return ""
    scored.sort(key=lambda item: -item[0])
    blocks = []
    per_file: dict = {}
    for _, rel, para in scored:
        if per_file.get(rel, 0) >= 2:
            continue
        per_file[rel] = per_file.get(rel, 0) + 1
        blocks.append(f"[{rel}]\n{para[:800]}")
        if len(blocks) >= limit:
            break
    return "\n\n".join(blocks)
