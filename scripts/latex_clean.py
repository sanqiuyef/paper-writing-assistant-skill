
# ---------------------------------------------------------------------------
# 本文件自 scipilot-writing-skill (https://github.com/Haojae/scipilot-writing-skill)
# v1.0.0 引入，按 MIT License 授权使用（Copyright (c) 2026 Haojae）。
# 2026-11-14 扩展：$$...$$、数学环境、引用/URL 命令参数、表格 &、\verb/verbatim
# 与行首注释均纳入掩蔽，避免自动转义破坏公式与命令参数。
# ---------------------------------------------------------------------------
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scipilot-writing-skill :: latex_clean.py
========================================
LaTeX 文本的"纯净 + 转义"安全网。润色英文论文片段时，最容易翻车的是把
`95%` / `model_v1` / `R&D` 直接塞进正文导致编译错误或注释掉整行。本脚本：

  1. escape_latex(text)  —— 自动转义数学跨度**之外**的 % & # _（已转义的跳过），
                            保留 $...$、\\(..\\)、\\[..\\] 内的内容原样。
  2. check_latex(text)   —— 报告未转义特殊字符、`$` 是否配平、是否误用 Markdown、
                            以及擅自添加的强调命令数量。

注意：escape 只动正文里的裸特殊字符；它不会去改 `\\cite{a_b}`、`\\label{sec:x}`
这类命令参数（因为下划线在参数里通常无害）。要严格控制请人工复核 check 的输出。

用法
----
    python latex_clean.py draft.tex --check            # 只体检，不改
    python latex_clean.py draft.tex                     # 转义后输出到 stdout
    python latex_clean.py draft.tex --in-place         # 原地写回（先备份 .bak）
"""
from __future__ import annotations

import argparse
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SPECIALS = ("%", "&", "#", "_")

# 数学环境整段原样保留；表格环境只保护 &（列分隔符），单元格文本仍按正文处理。
MATH_ENVS = {
    "math", "displaymath", "equation", "equation*", "align", "align*",
    "gather", "gather*", "multline", "multline*", "eqnarray", "eqnarray*",
    "array", "matrix", "pmatrix", "bmatrix", "vmatrix", "Vmatrix",
    "cases", "split", "aligned", "gathered", "multlined", "subequations",
}
TABLE_ENVS = {"tabular", "tabular*", "tabularx", "longtable", "tabulary"}
# 参数内允许出现裸 _ # % & 的命令：引用、标签、URL、文件路径等。
LITERAL_COMMAND_RX = re.compile(
    r"\\(?:cite|citep|citet|ref|eqref|label|url|href|includegraphics|"
    r"input|include|bibliography)\*?"
)


def _mark(mask: list, start: int, end: int) -> None:
    for index in range(max(0, start), min(len(mask), end)):
        mask[index] = True


def _consume_command_args(text: str, position: int) -> int:
    """Consume up to three optional/brace arguments after a command name."""
    n = len(text)
    index = position
    for _ in range(3):
        while index < n and text[index] in " \t":
            index += 1
        if index < n and text[index] == "[":
            close = text.find("]", index + 1)
            if close == -1:
                return n
            index = close + 1
            continue
        if index < n and text[index] == "{":
            depth = 0
            cursor = index
            while cursor < n:
                if text[cursor] == "{":
                    depth += 1
                elif text[cursor] == "}":
                    depth -= 1
                    if depth == 0:
                        cursor += 1
                        break
                cursor += 1
            if depth != 0:
                return n
            index = cursor
            continue
        break
    return index


def _math_mask(text: str) -> list:
    """标记数学/命令/表格分隔符/注释等不可自动改写的字符。

    覆盖 ``$...$``、``$$...$$``、``\\(...\\)``、``\\[...\\]``、数学环境、
    ``\\verb``、``verbatim``、引用/URL/文件路径命令参数、表格 ``&`` 与行首注释。
    """
    n = len(text)
    mask = [False] * n

    for match in re.finditer(r"^[ \t]*%.*$", text, re.MULTILINE):
        _mark(mask, match.start(), match.end())

    i = 0
    while i < n:
        if text.startswith("$$", i):
            close = text.find("$$", i + 2)
            end = n if close == -1 else close + 2
            _mark(mask, i, end)
            i = end
            continue

        char = text[i]
        if char == "$":
            cursor = i + 1
            while cursor < n:
                if text[cursor] == "$" and (cursor == 0 or text[cursor - 1] != "\\"):
                    break
                cursor += 1
            end = n if cursor >= n else cursor + 1
            _mark(mask, i, end)
            i = end
            continue

        if char == "\\":
            if text.startswith("\\(", i):
                close = text.find("\\)", i + 2)
                end = n if close == -1 else close + 2
                _mark(mask, i, end)
                i = end
                continue
            if text.startswith("\\[", i):
                close = text.find("\\]", i + 2)
                end = n if close == -1 else close + 2
                _mark(mask, i, end)
                i = end
                continue

            verb = re.match(r"\\verb\*?", text[i:])
            if verb:
                cursor = i + verb.end()
                if cursor < n:
                    delimiter = text[cursor]
                    close = text.find(delimiter, cursor + 1)
                    cursor = n if close == -1 else close + 1
                _mark(mask, i, cursor)
                i = cursor
                continue

            begin = re.match(r"\\begin\{([^}]+)\}", text[i:])
            if begin:
                env = begin.group(1)
                end_tag = "\\end{" + env + "}"
                close = text.find(end_tag, i + begin.end())
                end = n if close == -1 else close + len(end_tag)
                if env in MATH_ENVS or env == "verbatim":
                    _mark(mask, i, end)
                    i = end
                    continue
                if env in TABLE_ENVS:
                    for cursor in range(i, end):
                        if text[cursor] == "&" and (cursor == 0 or text[cursor - 1] != "\\"):
                            mask[cursor] = True
                _mark(mask, i, i + begin.end())
                i += begin.end()
                continue

            literal = LITERAL_COMMAND_RX.match(text, i)
            if literal:
                end = _consume_command_args(text, literal.end())
                _mark(mask, i, end)
                i = end
                continue

            mask[i] = True
            if i + 1 < n:
                mask[i + 1] = True
            i += 2
            continue

        i += 1
    return mask


def escape_report(text: str) -> tuple[str, dict]:
    """转义并返回每类字符的改动计数。"""
    mask = _math_mask(text)
    out = []
    counts = {char: 0 for char in SPECIALS}
    for i, c in enumerate(text):
        if c in SPECIALS and not mask[i]:
            out.append("\\" + c)
            counts[c] += 1
        else:
            out.append(c)
    return "".join(out), {key: value for key, value in counts.items() if value}


def escape_latex(text: str) -> str:
    """转义数学外、未转义的 % & # _。"""
    return escape_report(text)[0]


def check_latex(text: str) -> list:
    """返回 [(severity, message), ...]。severity ∈ {FAIL, WARN, INFO}。"""
    issues = []
    mask = _math_mask(text)
    # 未转义特殊字符
    sev = {"%": "FAIL", "&": "WARN", "#": "INFO", "_": "INFO"}
    cnt = {k: 0 for k in SPECIALS}
    for i, c in enumerate(text):
        if c in SPECIALS and not mask[i] and (i == 0 or text[i - 1] != "\\"):
            cnt[c] += 1
    for ch in SPECIALS:
        if cnt[ch]:
            issues.append((sev[ch], f"未转义 '{ch}' ×{cnt[ch]} → 应为 '\\{ch}'"))
    # $ 配平
    n_dollar = sum(1 for i, c in enumerate(text) if c == "$" and (i == 0 or text[i - 1] != "\\"))
    if n_dollar % 2:
        issues.append(("FAIL", f"行内数学 '$' ×{n_dollar}（奇数）未配平"))
    # Markdown 误用
    md = re.findall(r"\*\*[^*]+\*\*|(?<!\w)__[^_]+__", text)
    if md:
        issues.append(("WARN", f"疑似 Markdown 加粗 ×{len(md)} → LaTeX 应用 \\textbf{{}}"))
    # 擅自强调（风格提示）
    emph = len(re.findall(r"\\(?:textbf|emph|textit)\{", text))
    if emph:
        issues.append(("INFO", f"强调命令 \\textbf/\\emph/\\textit ×{emph}（顶刊正文倾向少用，确认是否原文已有）"))
    return issues


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="LaTeX 纯净 + 转义工具")
    ap.add_argument("path", help="LaTeX 文件路径；'-' 读 stdin")
    ap.add_argument("--check", action="store_true", help="只体检，不输出转义结果")
    ap.add_argument("--in-place", action="store_true", help="原地写回（生成 .bak 备份）")
    args = ap.parse_args(argv)

    text = sys.stdin.read() if args.path == "-" else open(args.path, encoding="utf-8").read()

    issues = check_latex(text)
    for sev, msg in issues:
        print(f"[{sev}] {msg}", file=sys.stderr)
    has_fail = any(s == "FAIL" for s, _ in issues)

    if args.check:
        print(("FAIL" if has_fail else "OK"), file=sys.stderr)
        return 2 if has_fail else 0

    cleaned = escape_latex(text)
    if args.in_place and args.path != "-":
        open(args.path + ".bak", "w", encoding="utf-8").write(text)
        open(args.path, "w", encoding="utf-8").write(cleaned)
        print(f"written: {args.path}  (backup: {args.path}.bak)", file=sys.stderr)
    else:
        sys.stdout.write(cleaned)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
