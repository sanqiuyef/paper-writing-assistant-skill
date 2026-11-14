#!/usr/bin/env python3
"""Build a local regression set from real drafts or Markdown corpora.

The output stays under ``tests/regression_local/`` (gitignored) so third-party
paper text is never published. Run the checker after generation:

    python tests/build_regression_local.py --source 论文初稿.md --limit 30
    python tests/run_regression.py --cases tests/regression_local/cases.json --write-expected
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "tests" / "regression_local" / "cases.json"
SKIP_PREFIXES = ("#", "|", "**", ">", "- ", "```", "![")
NOISE = ("学号", "密级", "指导教师", "原创性声明", "参考文献")


def iter_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    return sorted(
        path
        for path in source.rglob("*")
        if path.suffix.lower() in {".md", ".txt"}
        and "regression_local" not in path.parts
        and ".git" not in path.parts
    )


def iter_paragraphs(path: Path, min_chars: int, max_chars: int):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for item in re.split(r"\n\s*\n", text):
        paragraph = item.strip()
        if not (min_chars <= len(paragraph) <= max_chars):
            continue
        if paragraph.startswith(SKIP_PREFIXES):
            continue
        if any(noise in paragraph for noise in NOISE):
            continue
        yield paragraph


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从真实稿件构建本地回归集")
    parser.add_argument("--source", required=True, help="文件或目录（.md/.txt）")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--min-chars", type=int, default=200)
    parser.add_argument("--max-chars", type=int, default=1500)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    source = Path(args.source)
    candidates = []
    for path in iter_files(source):
        for paragraph in iter_paragraphs(path, args.min_chars, args.max_chars):
            candidates.append((path, paragraph))

    if not candidates:
        raise SystemExit("没有找到符合条件的段落，检查 --source / --min-chars")

    if len(candidates) > args.limit:
        step = len(candidates) / args.limit
        picked = [candidates[min(int(index * step), len(candidates) - 1)] for index in range(args.limit)]
    else:
        picked = candidates

    cases = []
    for index, (path, paragraph) in enumerate(picked, 1):
        checks = {
            "defensive": {"section": "body"},
            "ai_style": {},
            "lint": {"mode": "plain", "language": "auto"},
        }
        if path.suffix.lower() == ".tex":
            checks["latex"] = {}
        cases.append(
            {
                "id": f"real_{index:03d}",
                "source": str(path),
                "text": paragraph,
                "checks": checks,
            }
        )

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"cases": cases}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(cases)} cases -> {output}")
    print("next: python tests/run_regression.py --cases", output, "--write-expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
