"""Fixed CLI cases shared by tests/test_scripts.py and tests/update_expected.py."""

CASES = [
    {
        "name": "check_zh",
        "script": "check_academic_language.py",
        "args": [
            "--text",
            "近年来，值得注意的是，本文提出的方法具有重要价值。",
            "--language",
            "auto",
        ],
        "exit_code": 0,
    },
    {
        "name": "replace_apply",
        "script": "replace_ai_phrases.py",
        "args": [
            "--text",
            "值得注意的是，本文方法具有重要价值。",
            "--language",
            "auto",
            "--apply",
        ],
        "exit_code": 0,
    },
    {
        "name": "fill_abstract",
        "script": "fill_section_template.py",
        "args": ["--section", "abstract", "--paper-type", "general", "--language", "zh"],
        "exit_code": 0,
    },
    {
        "name": "fill_cover_letter",
        "script": "fill_section_template.py",
        "args": ["--section", "cover_letter", "--language", "zh"],
        "exit_code": 0,
    },
    {
        "name": "outline_general",
        "script": "generate_outline.py",
        "args": ["--language", "zh", "--paper-type", "general"],
        "exit_code": 0,
    },
    {
        "name": "lint_latex_fail",
        "script": "lint_writing.py",
        "args": ["--text", "精度提升 95% 且 **加粗**。", "--mode", "latex", "--language", "zh"],
        "exit_code": 1,
    },
    {
        "name": "defensive_scan",
        "script": "check_defensive_writing.py",
        "args": [
            "--text",
            "本文方法效果有限，仍明显落后于基线。有人可能会问，这是否意味着方法无效？",
            "--section",
            "abstract",
        ],
        "exit_code": 1,
    },
    {
        "name": "defensive_clean",
        "script": "check_defensive_writing.py",
        "args": ["--text", "本文方法在21场降雨上的 RMSE 为 8.78 mm。"],
        "exit_code": 0,
    },
    {
        "name": "defensive_discussion",
        "script": "check_defensive_writing.py",
        "args": [
            "--text",
            "本研究的局限在于样本仅覆盖21场降雨，尚需在更多城市验证。",
            "--section",
            "discussion",
        ],
        "exit_code": 0,
    },
    {
        "name": "latex_protect",
        "script": "latex_sanitize.py",
        "args": ["--text", "$$x_1=y_1$$ \\cite{model_v1}", "--fix"],
        "exit_code": 0,
    },
    {
        "name": "latex_fix",
        "script": "latex_sanitize.py",
        "args": ["--text", "95% 的样本 & 5 个变量", "--fix"],
        "exit_code": 1,
    },
]
