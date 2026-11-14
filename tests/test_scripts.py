#!/usr/bin/env python3
"""Deterministic CLI contract tests for paper-writing-assistant.

Run from the skill root:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from cases import CASES

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
EXPECTED = Path(__file__).resolve().parent / "expected_outputs"


def run_script(script: str, args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPTS / script), *args],
        cwd=SCRIPTS,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=merged,
    )


class ScriptContractTest(unittest.TestCase):
    def test_fixed_cases(self) -> None:
        for case in CASES:
            with self.subTest(case=case["name"]):
                result = run_script(case["script"], case["args"])
                self.assertEqual(result.returncode, case["exit_code"], result.stderr)
                payload = json.loads(result.stdout)
                self.assertTrue(payload["ok"], payload)
                expected = json.loads((EXPECTED / f"{case['name']}.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["data"], expected)

    def test_usage_error_exit_2(self) -> None:
        result = run_script("check_academic_language.py", ["--text", "文本", "--language", "fr"])
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])

    def test_missing_api_key_exit_3(self) -> None:
        result = run_script(
            "rewrite_academic_text.py",
            ["--text", "值得注意的是，本文方法具有重要价值。"],
            env={"DEEPSEEK_API_KEY": ""},
        )
        self.assertEqual(result.returncode, 3)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("DEEPSEEK_API_KEY", payload["error"])

    def test_rewrite_dry_run_no_network(self) -> None:
        result = run_script(
            "rewrite_academic_text.py",
            ["--text", "值得注意的是，本文方法具有重要价值。", "--dry-run"],
            env={"DEEPSEEK_API_KEY": ""},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["data"]["dry_run"])
        self.assertIn("system_prompt", payload["data"])
        self.assertIn("AI 腔参考清单", payload["data"]["system_prompt"])

    def test_help_every_entrypoint(self) -> None:
        for script in (
            "check_academic_language.py",
            "replace_ai_phrases.py",
            "fill_section_template.py",
            "generate_outline.py",
            "rewrite_academic_text.py",
            "fact_integrity_check.py",
            "lint_writing.py",
            "latex_sanitize.py",
            "check_defensive_writing.py",
        ):
            with self.subTest(script=script):
                result = run_script(script, ["--help"])
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
