# 测试与评测

| 套件 | 命令 | 内容 |
|:---|:---|:---|
| 契约/结构 | `python -m unittest discover -s tests -v` | 入口、固定输出、退出码、LaTeX、事实核对、防御性、AI 结构 |
| 合成回归 | `python tests/run_regression.py --verbose` | `regression_cases.json` 中 19 条自写段落 |
| 真实段落回归 | `python tests/build_regression_local.py --source <草稿> --limit 30` | 生成 `regression_local/cases.json`（gitignored） |
| 英/综述回归 | `--language en` 与 `--path-contains review` | 各 20 段，生成 `en_cases.json` / `review_cases.json`（gitignored） |
| 段落骨架报告 | `python scripts/check_ai_style.py --input-file <稿> --report report.html` | 自包含 HTML：段落骨架表、句长网格、问题清单 |
| 触发评测 | `python tests/evaluate_triggers.py [--llm]` | `trigger_cases.json` 的 15 正 / 10 负样例 |

## 回归用例格式

```json
{
  "id": "def_self_dep",
  "text": "待检查段落",
  "checks": {
    "defensive": {"section": "body", "verdict": "FAIL"},
    "ai_style": {"verdict": "WARN"},
    "lint": {"mode": "plain", "language": "zh", "verdict": "PASS"},
    "latex": {"verdict": "PASS"}
  }
}
```

- `verdict` 由 `--write-expected` 用当前检测结果回填；改动检测器后重新回填并人工复核差异。
- 真实稿件段落只放 `tests/regression_local/`，`.gitignore` 已排除；不要提交第三方论文原文或未发表数据。
- `build_regression_local.py` 默认抽取 200–1500 字、排除标题/表格/代码块/封面噪声，按等距抽样取 30 段（不足则全取）。

## 触发用例格式

```json
{"id": "pos_01", "prompt": "帮我润色这一段", "should_trigger": true, "expected_script": "lint_writing.py"}
```

- 词法基线从 `SKILL.md` 的 `description` 中提取触发词，再加少量同义词；只评估“是否触发”，不评估路由。
- `--llm` 把全部请求发给 DeepSeek，评估触发与脚本路由；需要 `DEEPSEEK_API_KEY`，一次调用完成。
- 改 description 或新增脚本后，同步更新 `trigger_cases.json`。

## 更新流程

```bash
python tests/update_expected.py                 # CLI 固定输出
python tests/run_regression.py --write-expected # 合成回归
python tests/evaluate_triggers.py --strict      # 触发基线
python -m unittest discover -s tests -v
```
