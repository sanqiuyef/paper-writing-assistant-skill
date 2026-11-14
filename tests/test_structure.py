"""Structural checks for the skill package (no model calls)."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class StructureTest(unittest.TestCase):
    def test_frontmatter(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        front = text.split("---", 2)[1]
        self.assertIn("name: paper-writing-assistant", front)
        description = re.search(r"^description: (.+)$", front, re.MULTILINE)
        self.assertIsNotNone(description)
        self.assertLessEqual(len(description.group(1).encode("utf-8")), 1024)
        self.assertLess(len(text.splitlines()), 500)

    def test_referenced_files_exist(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        referenced = {
            path
            for path in re.findall(r"`((?:scripts|references|assets|templates|config|tests)/[^`]+)`", text)
            if "<" not in path and "*" not in path
        }
        missing = [path for path in referenced if not (ROOT / path).exists()]
        self.assertEqual(missing, [], f"SKILL.md 引用了不存在的路径: {missing}")

    def test_required_engineering_files(self) -> None:
        for path in (
            "README.md",
            "config/defaults.json",
            "lifecycle.yaml",
            "agents/openai.yaml",
            "tests/test_scripts.py",
            "tests/expected_outputs/check_zh.json",
            "scripts/check_defensive_writing.py",
            "scripts/defensive_patterns.json",
            "scripts/fact_integrity_check.py",
            "scripts/check_ai_style.py",
            "tests/test_fact_integrity.py",
            "tests/test_ai_style.py",
            "templates/cover_letter_zh.md",
            "assets/profiles/general/sections_zh.md",
            "references/anti_defensive_writing.md",
        ):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)

    def test_no_mcp_runtime_dependency(self) -> None:
        for script in (ROOT / "scripts").glob("*.py"):
            body = script.read_text(encoding="utf-8")
            self.assertNotIn("import mcp", body, script.name)
            self.assertNotIn("from mcp", body, script.name)
            self.assertNotIn("mcp__", body, script.name)

    def test_lexicon_shape(self) -> None:
        data = json.loads((ROOT / "scripts/_lexicon.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["zh_words"]), 45)
        self.assertEqual(len(data["en_words"]), 78)


if __name__ == "__main__":
    unittest.main()
