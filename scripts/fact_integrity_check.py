#!/usr/bin/env python3
"""对比原文与改写稿，核对数值、单位、引用、术语与结论方向。

这是确定性事实核对，不是语义等价证明：它只能发现“数字/单位/引用/方向”
这类可直接比对的变化，语义漂移仍需人工复核。
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

import _common as C

TOOL = "fact_integrity_check"

UNIT_PATTERN = (
    r"(?:%|％|‰|℃|°C|km²|km2|m³|m3|km|cm|mm|m|h|min|s|ms|kg|g|t|L|mL|"
    r"GB|MB|KB|FPS|Hz|kHz|MHz|dB|Pa|kPa|MPa|W|kW|MW|V|A|mol|人|万|亿|元|"
    r"m/s|km/h|mm/h|mm/min)"
)
NUM_UNIT_RX = re.compile(
    r"(?<![A-Za-z0-9_.])(\d+(?:\.\d+)?)\s*(" + UNIT_PATTERN + r")(?![A-Za-z0-9_])"
)
NUM_BARE_RX = re.compile(r"(?<![A-Za-z0-9_.])(\d+(?:\.\d+)?)(?![A-Za-z0-9_.])")
CITE_RX = re.compile(r"\\(?:cite|citep|citet|ref|eqref)\*?(?:\[[^\]]*\])?\{([^}]*)\}")
BRACKET_CITE_RX = re.compile(r"\[(\d+(?:\s*[,，-]\s*\d+)*)\]")

DIRECTION_PAIRS = (
    ("提升", "下降"),
    ("提高", "降低"),
    ("增加", "减少"),
    ("上升", "下降"),
    ("高于", "低于"),
    ("优于", "劣于"),
    ("正相关", "负相关"),
    ("显著", "不显著"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = C.json_parser(
        TOOL,
        description="对比原文与改写稿的数值、单位、引用、术语与结论方向。",
        epilog="退出码：0 PASS/WARN；1 FAIL；2 参数或输入错误；3 运行时错误。",
    )
    parser.add_argument("--original", required=True, help="原文文件（UTF-8）")
    parser.add_argument("--revised", required=True, help="改写稿文件（UTF-8）")
    parser.add_argument("--terms", default="", help="必须保留的术语，逗号分隔（如模型名、数据集名）")
    parser.add_argument("--terms-file", help="术语清单文件，一行一个")
    parser.add_argument("--bracket-citations", action="store_true", help="把 [12] 形式的编号也当引用核对")
    parser.add_argument("--no-directions", action="store_true", help="跳过结论方向核对")
    return parser


def _normalize_number(value: str) -> str:
    try:
        return str(Decimal(value).normalize())
    except InvalidOperation:
        return value


def _normalize_unit(unit: str) -> str:
    return unit.replace("％", "%").replace("m3", "m³").replace("km2", "km²").lower()


def _context(text: str, start: int, end: int, width: int = 24) -> str:
    return text[max(0, start - width):min(len(text), end + width)].replace("\n", " ").strip()


def extract_numbers(text: str) -> list[dict]:
    """Return numeric claims with unit and source span; skip years and section refs."""
    items: list[dict] = []
    covered: list[tuple[int, int]] = []
    for match in NUM_UNIT_RX.finditer(text):
        covered.append(match.span())
        items.append(
            {
                "value": _normalize_number(match.group(1)),
                "unit": _normalize_unit(match.group(2)),
                "raw": match.group(0).strip(),
                "span": match.span(),
            }
        )
    for match in NUM_BARE_RX.finditer(text):
        if any(start <= match.start() < end for start, end in covered):
            continue
        value = match.group(1)
        try:
            number = float(value)
        except ValueError:
            continue
        if 1900 <= number <= 2099:
            continue
        prefix = text[max(0, match.start() - 2):match.start()]
        if re.search(r"[第图表式节章节\[]$", prefix):
            continue
        items.append(
            {
                "value": _normalize_number(value),
                "unit": "",
                "raw": value,
                "span": match.span(),
            }
        )
    items.sort(key=lambda item: item["span"][0])
    return items


def extract_citations(text: str, bracket: bool) -> list[str]:
    citations: list[str] = []
    for match in CITE_RX.finditer(text):
        for key in re.split(r"\s*[,，]\s*", match.group(1)):
            key = key.strip()
            if key:
                citations.append(key)
    if bracket:
        for match in BRACKET_CITE_RX.finditer(text):
            for key in re.split(r"\s*[,，-]\s*", match.group(1)):
                if key:
                    citations.append(f"[{key}]")
    return citations


def _key(item: dict) -> tuple[str, str]:
    return item["value"], item["unit"]


def _display(items: list[dict], limit: int = 5) -> list[str]:
    return [f"{item['raw']}（{_context(item.get('_text', ''), *item['span'])}）" for item in items[:limit]]


def compare_numbers(original: str, revised: str) -> list[dict]:
    orig_items = extract_numbers(original)
    rev_items = extract_numbers(revised)
    for item in orig_items:
        item["_text"] = original
    for item in rev_items:
        item["_text"] = revised

    orig_counter = Counter(_key(item) for item in orig_items)
    rev_counter = Counter(_key(item) for item in rev_items)
    missing_keys = orig_counter - rev_counter
    added_keys = rev_counter - orig_counter

    issues: list[dict] = []

    def pick(items: list[dict], keys: Counter) -> list[dict]:
        picked = []
        remaining = Counter(keys)
        for item in items:
            key = _key(item)
            if remaining[key] > 0:
                picked.append(item)
                remaining[key] -= 1
        return picked

    missing = pick(orig_items, missing_keys)
    added = pick(rev_items, added_keys)

    # Same numeric value but different unit is the highest-risk silent change.
    orig_by_value: dict[str, set[str]] = {}
    rev_by_value: dict[str, set[str]] = {}
    for item in orig_items:
        orig_by_value.setdefault(item["value"], set()).add(item["unit"])
    for item in rev_items:
        rev_by_value.setdefault(item["value"], set()).add(item["unit"])
    unit_conflicts = []
    for value in sorted(set(orig_by_value) & set(rev_by_value)):
        if orig_by_value[value] != rev_by_value[value]:
            unit_conflicts.append(
                {
                    "value": value,
                    "original_units": sorted(orig_by_value[value]),
                    "revised_units": sorted(rev_by_value[value]),
                }
            )

    conflict_values = {item["value"] for item in unit_conflicts}
    missing = [item for item in missing if item["value"] not in conflict_values]
    added = [item for item in added if item["value"] not in conflict_values]

    if unit_conflicts:
        issues.append(
            {
                "severity": "FAIL",
                "code": "FACT_UNIT_CHANGED",
                "message": f"同一数值的单位发生变化（{len(unit_conflicts)} 处）",
                "examples": [
                    f"{item['value']}: {','.join(item['original_units'])} → {','.join(item['revised_units'])}"
                    for item in unit_conflicts[:5]
                ],
            }
        )

    if missing:
        issues.append(
            {
                "severity": "FAIL",
                "code": "FACT_NUMBER_MISSING",
                "message": f"改写稿缺少原文数值（{len(missing)} 处）",
                "examples": _display(missing),
            }
        )
    if added:
        issues.append(
            {
                "severity": "FAIL",
                "code": "FACT_NUMBER_ADDED",
                "message": f"改写稿新增原文没有的数值（{len(added)} 处）",
                "examples": _display(added),
            }
        )

    if not missing and not added and not unit_conflicts:
        orig_sequence = [item["value"] for item in orig_items]
        rev_sequence = [item["value"] for item in rev_items]
        if orig_sequence != rev_sequence:
            issues.append(
                {
                    "severity": "WARN",
                    "code": "FACT_NUMBER_ORDER",
                    "message": "数值集合一致但出现顺序改变，确认是否影响指代",
                    "examples": [
                        " → ".join(item["raw"] for item in orig_items[:6]),
                        " → ".join(item["raw"] for item in rev_items[:6]),
                    ],
                }
            )

    return issues


def compare_citations(original: str, revised: str, bracket: bool) -> list[dict]:
    orig = Counter(extract_citations(original, bracket))
    rev = Counter(extract_citations(revised, bracket))
    missing = orig - rev
    added = rev - orig
    issues = []
    if missing:
        issues.append(
            {
                "severity": "FAIL",
                "code": "FACT_CITATION_MISSING",
                "message": f"改写稿缺少原文引用标记（{sum(missing.values())} 处）",
                "examples": list(missing.elements())[:10],
            }
        )
    if added:
        issues.append(
            {
                "severity": "FAIL",
                "code": "FACT_CITATION_ADDED",
                "message": f"改写稿新增原文没有的引用标记（{sum(added.values())} 处）",
                "examples": list(added.elements())[:10],
            }
        )
    return issues


def load_terms(args: argparse.Namespace) -> list[str]:
    terms = [item.strip() for item in args.terms.split(",") if item.strip()]
    if args.terms_file:
        path = Path(args.terms_file)
        if not path.is_file():
            raise C.UsageError(f"术语文件不存在：{path}")
        terms.extend(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        )
    return list(dict.fromkeys(terms))


def compare_terms(original: str, revised: str, terms: list[str]) -> list[dict]:
    if not terms:
        return []
    missing = [term for term in terms if original.count(term) > revised.count(term)]
    if not missing:
        return []
    return [
        {
            "severity": "FAIL",
            "code": "FACT_TERM_MISSING",
            "message": f"改写稿遗漏受保护术语（{len(missing)} 个）",
            "examples": [
                f"{term}: {original.count(term)} → {revised.count(term)}" for term in missing[:10]
            ],
        }
    ]


def compare_directions(original: str, revised: str) -> list[dict]:
    flipped = []
    for positive, negative in DIRECTION_PAIRS:
        orig_pos, orig_neg = original.count(positive), original.count(negative)
        rev_pos, rev_neg = revised.count(positive), revised.count(negative)
        if orig_pos and not orig_neg and rev_neg and not rev_pos:
            flipped.append(f"{positive} → {negative}")
        elif orig_neg and not orig_pos and rev_pos and not rev_neg:
            flipped.append(f"{negative} → {positive}")
    if not flipped:
        return []
    return [
        {
            "severity": "FAIL",
            "code": "FACT_DIRECTION_FLIPPED",
            "message": f"结论方向可能反转（{len(flipped)} 处）",
            "examples": flipped[:10],
        }
    ]


def run(args: argparse.Namespace) -> dict:
    original = C.read_text(None, args.original, "original")
    revised = C.read_text(None, args.revised, "revised")
    if not original.strip() or not revised.strip():
        raise C.UsageError("原文与改写稿都不能为空")

    issues = []
    issues.extend(compare_numbers(original, revised))
    issues.extend(compare_citations(original, revised, args.bracket_citations))
    issues.extend(compare_terms(original, revised, load_terms(args)))
    if not args.no_directions:
        issues.extend(compare_directions(original, revised))

    fail = sum(1 for item in issues if item["severity"] == "FAIL")
    warn = sum(1 for item in issues if item["severity"] == "WARN")
    verdict = "FAIL" if fail else ("WARN" if warn else "PASS")
    return {
        "verdict": verdict,
        "fail": fail,
        "warn": warn,
        "stats": {
            "original_chars": len(original),
            "revised_chars": len(revised),
            "numbers_original": len(extract_numbers(original)),
            "numbers_revised": len(extract_numbers(revised)),
            "citations_original": len(extract_citations(original, args.bracket_citations)),
            "citations_revised": len(extract_citations(revised, args.bracket_citations)),
        },
        "issues": issues,
        "note": "确定性核对只覆盖数值/单位/引用/术语/方向；语义等价、指代与论证强度仍需人工复核。",
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
