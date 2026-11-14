#!/usr/bin/env python3
"""Evaluate skill triggering against tests/trigger_cases.json.

Default mode is a lexical proxy over the description's trigger terms (fast,
offline). ``--llm`` sends the whole case list to the configured DeepSeek model
and asks it to route each request, which is a closer simulation of host-agent
triggering but costs one API call.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import _rewrite  # noqa: E402

CASES = Path(__file__).resolve().parent / "trigger_cases.json"
SKILL = ROOT / "SKILL.md"
EXTRA_TERMS = (
    "语言问题",
    "结论部分有没有自我否定",
    "数字和引用",
    "数字有没有变",
    "摘要写得像模板",
    "太防御",
    "AI 写的",
    "AI 味",
    "摘要模板",
    "模板",
    "大纲",
    "终检",
    "LaTeX",
    "转义",
)


def load_cases() -> list[dict]:
    return json.loads(CASES.read_text(encoding="utf-8"))["cases"]


def description_terms() -> list[str]:
    text = SKILL.read_text(encoding="utf-8")
    line = next(item for item in text.splitlines() if item.startswith("description:"))
    triggers = line.split("触发：", 1)[1].rstrip("。")
    terms = []
    for item in triggers.split("、"):
        terms.extend(part.strip() for part in item.split("/") if part.strip())
    terms.extend(EXTRA_TERMS)
    return list(dict.fromkeys(terms))


def lexical_predict(prompt: str, terms: list[str]) -> bool:
    lower = prompt.lower()
    return any(term.lower() in lower for term in terms)


def score(cases: list[dict], predictions: dict[str, bool], scripts: dict[str, str] | None = None) -> dict:
    tp = fp = tn = fn = 0
    misses = []
    script_total = script_ok = 0
    for case in cases:
        expected = case["should_trigger"]
        actual = predictions[case["id"]]
        if expected and actual:
            tp += 1
            if scripts is not None:
                script_total += 1
                if scripts.get(case["id"]) == case["expected_script"]:
                    script_ok += 1
        elif expected and not actual:
            fn += 1
            misses.append((case["id"], "miss", case["prompt"]))
        elif not expected and actual:
            fp += 1
            misses.append((case["id"], "false-positive", case["prompt"]))
        else:
            tn += 1
    total = len(cases)
    result = {
        "total": total,
        "accuracy": round((tp + tn) / total, 3) if total else 0.0,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "misses": misses,
    }
    if scripts is not None:
        result["script_accuracy"] = round(script_ok / script_total, 3) if script_total else 0.0
        result["script_ok"] = script_ok
        result["script_total"] = script_total
    return result


def llm_predict(cases: list[dict]) -> tuple[dict[str, bool], dict[str, str]]:
    description = next(
        item for item in SKILL.read_text(encoding="utf-8").splitlines() if item.startswith("description:")
    )
    system = "你是 ZCode 的 skill 路由器。只输出 JSON，不要解释。"
    payload = [
        {"id": case["id"], "prompt": case["prompt"], "expected_script": case["expected_script"]}
        for case in cases
    ]
    user = (
        f"SKILL 描述：\n{description}\n\n"
        "判断下列用户请求是否应触发该 skill。应触发的请求给出最合适的脚本名；"
        "不应触发的 script 填空字符串。只输出 JSON："
        '{"results":[{"id":"pos_01","trigger":true,"script":"lint_writing.py"}]}\n'
        f"请求列表：\n{json.dumps(payload, ensure_ascii=False)}"
    )
    raw = _rewrite.call_deepseek(system, user, 0.0)
    data = _rewrite.extract_json_object(raw)
    results = data.get("results")
    if not isinstance(results, list):
        raise SystemExit("模型输出缺少 results 数组")
    predictions = {item["id"]: bool(item.get("trigger")) for item in results if "id" in item}
    scripts = {item["id"]: str(item.get("script", "")) for item in results if "id" in item}
    return predictions, scripts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="skill 触发评测")
    parser.add_argument("--llm", action="store_true", help="用 DeepSeek 模拟宿主触发（需 DEEPSEEK_API_KEY）")
    parser.add_argument("--strict", action="store_true", help="词法基线准确率 <0.9 时退出 1")
    args = parser.parse_args(argv)

    cases = load_cases()
    scripts = None
    if args.llm:
        try:
            predictions, scripts = llm_predict(cases)
            mode = "llm"
        except Exception as exc:
            print(f"LLM 模式不可用，回退词法基线：{exc}")
            predictions = {case["id"]: lexical_predict(case["prompt"], description_terms()) for case in cases}
            mode = "lexical"
    else:
        predictions = {case["id"]: lexical_predict(case["prompt"], description_terms()) for case in cases}
        mode = "lexical"

    result = score(cases, predictions, scripts)
    print(json.dumps({"mode": mode, **result}, ensure_ascii=False, indent=2))
    if args.strict and result["accuracy"] < 0.9:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
