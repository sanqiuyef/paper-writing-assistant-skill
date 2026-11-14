#!/usr/bin/env python3
"""Run regression cases against the deterministic checkers.

Case schema::

    {
      "id": "def_self",
      "text": "...",
      "checks": {
        "defensive": {"section": "body", "verdict": "FAIL"},
        "ai_style": {"verdict": "WARN"},
        "lint": {"mode": "plain", "language": "zh", "verdict": "WARN"},
        "latex": {"verdict": "FAIL"}
      }
    }

Use ``--write-expected`` after an intentional behaviour change (only for
synthetic or locally-owned text; never publish third-party paper paragraphs).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_ai_style  # noqa: E402
import check_defensive_writing  # noqa: E402
import latex_sanitize  # noqa: E402
import lint_writing  # noqa: E402


def evaluate(case: dict) -> dict:
    text = case["text"]
    results = {}
    for tool, config in case.get("checks", {}).items():
        if tool == "defensive":
            data = check_defensive_writing.run(
                argparse.Namespace(
                    text=text,
                    input_file=None,
                    section=config.get("section", "body"),
                    strict=config.get("strict", False),
                )
            )
            results[tool] = data["verdict"]
        elif tool == "ai_style":
            data = check_ai_style.run(
                argparse.Namespace(
                    text=text,
                    input_file=None,
                    language=config.get("language", "auto"),
                )
            )
            results[tool] = data["verdict"]
        elif tool == "lint":
            data = lint_writing.run(
                argparse.Namespace(
                    text=text,
                    input_file=None,
                    mode=config.get("mode", "plain"),
                    language=config.get("language", "auto"),
                )
            )
            results[tool] = data["verdict"]
        elif tool == "latex":
            data = latex_sanitize.run(
                argparse.Namespace(text=text, input_file=None, fix=True)
            )
            has_fail = any(item["severity"] == "FAIL" for item in data["problems"])
            results[tool] = "FAIL" if has_fail else "PASS"
        else:
            raise SystemExit(f"未知检查项：{tool}")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="回归用例执行器")
    parser.add_argument(
        "--cases",
        default=str(Path(__file__).resolve().parent / "regression_cases.json"),
    )
    parser.add_argument("--write-expected", action="store_true", help="用当前检测结果回填 verdict")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    path = Path(args.cases)
    payload = json.loads(path.read_text(encoding="utf-8"))
    failures = []
    for case in payload["cases"]:
        actual = evaluate(case)
        if args.write_expected:
            for tool, verdict in actual.items():
                case.setdefault("checks", {}).setdefault(tool, {})["verdict"] = verdict
            continue
        for tool, verdict in actual.items():
            expected = case.get("checks", {}).get(tool, {}).get("verdict")
            if expected is None:
                continue
            if expected != verdict:
                failures.append((case["id"], tool, expected, verdict))
                if args.verbose:
                    print(f"FAIL {case['id']} / {tool}: expected {expected}, got {verdict}")

    if args.write_expected:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"updated {len(payload['cases'])} cases -> {path}")
        return 0

    print(f"cases={len(payload['cases'])} failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
