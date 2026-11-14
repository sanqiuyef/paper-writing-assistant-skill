#!/usr/bin/env python3
"""Regenerate tests/expected_outputs/*.json from the current scripts.

Run after an intentional behaviour change:
    python tests/update_expected.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cases import CASES

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "expected_outputs"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "scripts" / case["script"]), *case["args"]],
            cwd=ROOT / "scripts",
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != case["exit_code"]:
            print(f"FAIL {case['name']}: exit {result.returncode} != {case['exit_code']}")
            print(result.stderr[:500])
            return 1
        payload = json.loads(result.stdout)
        (OUT / f"{case['name']}.json").write_text(
            json.dumps(payload["data"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("wrote", case["name"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
