# Paper Writing Assistant

中英文论文写作、润色、机检与降 AI 味的本地 Agent Skill。能力全部落在 `scripts/`，按需单独调用，不依赖 MCP 进程。

## 能力

| 脚本 | 用途 |
|:---|:---|
| `check_academic_language.py` | 语料级 AI 标记词检查，给替换建议 |
| `check_ai_style.py` | 结构级 AI 风格检测：模板腔、节奏、证据密度、连接词；`--report` 输出段落骨架 HTML |
| `replace_ai_phrases.py` | AI 腔用词检测；`--apply` 插入 `[[建议]]` 占位符 |
| `fill_section_template.py` | 章节 / 投稿信 / 审稿回复模板，支持 `{{占位符}}` |
| `generate_outline.py` | 论文大纲与配图方案 |
| `rewrite_academic_text.py` | DeepSeek 降 AI 味改写，带数字编造防线；`--dry-run` 只组装提示词、不发请求 |
| `fact_integrity_check.py` | 对比原文/改写稿的数值、单位、引用、术语与结论方向 |
| `lint_writing.py` | 确定性写作质量门控，PASS / WARN / FAIL |
| `check_defensive_writing.py` | 防御性写作检测：自贬、叠甲、预演质疑、过程汇报、括号摊底、叠层模糊、边界重复、反向夸大 |
| `latex_sanitize.py` | LaTeX 转义体检与修复 |

配套 `SKILL.md` 包含深度润色工作流、三段式交付、反防御性写作（发布会原则）与引用诚信铁律。

## 安装

```bash
git clone https://github.com/sanqiuyef/paper-writing-assistant-skill.git
cd paper-writing-assistant-skill
```

作为 ZCode / Claude Code 等支持 `SKILL.md` 的 agent skill 使用：

```bash
# 项目级
mkdir -p .zcode/skills
cp -r paper-writing-assistant-skill .zcode/skills/paper-writing-assistant

# 或用户级
cp -r paper-writing-assistant-skill ~/.zcode/skills/paper-writing-assistant

# Claude Code / Codex 等支持 SKILL.md 的工具
cp -r paper-writing-assistant-skill ~/.claude/skills/paper-writing-assistant
```

重启 agent 后生效。

## 环境

- Python ≥ 3.10。
- 仅 `rewrite_academic_text.py` 需要 `requests` 与 `DEEPSEEK_API_KEY`；其余脚本只用标准库。

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 DEEPSEEK_API_KEY，或在终端 export
```

Windows 控制台建议加 `-X utf8`，避免 GBK 乱码。

## 数据与隐私

- 除 `rewrite_academic_text.py` 外，所有脚本只在本地读写，不发起网络请求。
- `rewrite_academic_text.py` 会把待改写正文、可选范文片段与本地语料检索结果发送到 `config/defaults.json` 或 `DEEPSEEK_API_URL` 指定的端点。未发表数据、审稿材料、保密项目内容在发送前必须获得作者明确同意。
- 不想外发时用 `--dry-run`：只返回 `system_prompt` 与 `user_prompt`，由宿主 agent 自行改写，零网络请求。
- API key 只放环境变量或 `.env`（已在 `.gitignore`），不要写进脚本或提交记录。
- 按目标期刊与学校要求披露 AI 使用；本 skill 的目标是表达质量与可核验性，不承诺规避任何 AI 检测。

## 快速开始

```bash
# 1) AI 词检查（dry-run）
python -X utf8 scripts/check_academic_language.py --input-file section3.md

# 2) 章节模板
python -X utf8 scripts/fill_section_template.py --section abstract --paper-type general

# 3) 写作机检（Word 载体；FAIL 时退出码 1）
python -X utf8 scripts/lint_writing.py --input-file section3.md --mode word --language zh

# 4) LaTeX 体检与修复
python -X utf8 scripts/latex_sanitize.py --input-file draft.tex --fix

# 5) 降 AI 味：先看结构，再改写
python -X utf8 scripts/check_ai_style.py --input-file section3.md --report 骨架报告.html
python -X utf8 scripts/rewrite_academic_text.py --input-file section3.md --style academic --kb zh

# 5b) 不外发：只组装提示词，交给宿主 agent 改写
python -X utf8 scripts/rewrite_academic_text.py --input-file section3.md --dry-run

# 5c) 事实核对：数值/单位/引用/术语/结论方向
python -X utf8 scripts/fact_integrity_check.py --original section3_original.md --revised section3_revised.md --terms KAN-PC

# 6) 防御性写作检测（摘要/结论加 --section；终稿可加 --strict）
python -X utf8 scripts/check_defensive_writing.py --input-file section3.md --section results
```

## 输出与退出码

stdout 始终是一个 JSON 对象：

- 成功：`{"ok": true, "tool": "...", "data": {...}}`
- 失败：`{"ok": false, "tool": "...", "error": "..."}`

| 退出码 | 含义 |
|:---|:---|
| 0 | 成功；lint=PASS/WARN；latex 无 FAIL |
| 1 | 门控不通过：lint=FAIL 或 latex 存在 FAIL |
| 2 | 参数或输入错误 |
| 3 | 运行时错误（模板/语料缺失、缺 API key、外部调用失败） |

## 语料来源

- **证据级检索（可选）**：若环境提供 `lancedb-search` MCP，用 `search_knowledge(query, search_mode="hybrid")` 或 `get_document(filepath)` 取原文，把命中段落写入文件后交给 `rewrite_academic_text.py --reference-file`。
- **离线兜底**：任意 Markdown 语料目录，用 `--kb-dir` 或 `PWA_KB_DIR` / `PWA_VAULT_DIR` 指定；也可写进 `config/defaults.json` 的 `vault_dir`。`--kb zh/en` 按段落语言过滤，`--kb <主题目录>` 限定范围。
- **范文集**：`assets/corpus/` 放自己的 few-shot 范文（已在 `.gitignore`）；仓库只附带自写示例 `assets/corpus.example/`，不分发第三方论文原文。

## 配置

`config/defaults.json`：

```json
{
  "vault_dir": "",
  "deepseek": {
    "endpoint": "https://api.deepseek.com/chat/completions",
    "model": "deepseek-chat",
    "timeout": 120
  }
}
```

同名环境变量优先：`PWA_KB_DIR`、`PWA_VAULT_DIR`、`DEEPSEEK_API_KEY`、`DEEPSEEK_API_URL`、`DEEPSEEK_MODEL`、`DEEPSEEK_TIMEOUT`。

## 测试与评测

### 契约测试

```bash
python -X utf8 -m unittest discover -s tests -v
```

覆盖 10 个入口、LaTeX 掩蔽、事实核对、防御性检测、AI 结构检测、固定输出对照、退出码 1/2/3、结构检查与 MCP 独立性；当前 38 项 unittest 全部通过。有意改行为后先运行：

```bash
python -X utf8 tests/update_expected.py
```

`tests/test_prompts.md` 提供 4 条人工评测提示词。

### 合成回归集

```bash
python -X utf8 tests/run_regression.py --verbose
```

`tests/regression_cases.json` 含 19 条自写段落，覆盖正常方法/结果、真实局限、自贬、叠甲、预演质疑、过程汇报、括号摊底、叠层模糊、边界重复、过度主张、模板腔、知网句式、Word 残留与 LaTeX 保护。判定写回 `checks.verdict`，改动检测器后用 `--write-expected` 更新并复核。

### 真实论文段落回归（本地）

真实稿件段落不随仓库分发。用本地文件生成 20–30 段回归集：

```bash
python -X utf8 tests/build_regression_local.py --source 论文初稿.md --limit 30
python -X utf8 tests/run_regression.py --cases tests/regression_local/cases.json --write-expected
```

`tests/regression_local/` 已 gitignore。本轮用 v8 稿生成 27 段：防御性 25 PASS / 2 WARN / 0 FAIL，AI 结构 21 PASS / 6 WARN / 0 FAIL，写作机检 20 PASS / 7 WARN / 0 FAIL。

英文学术稿与英文综述各 20 段（本地语料，不入库）：

```bash
python -X utf8 tests/build_regression_local.py --source <文献目录> --language en --limit 20 --out tests/regression_local/en_cases.json
python -X utf8 tests/build_regression_local.py --source <文献目录> --language en --path-contains review --limit 20 --out tests/regression_local/review_cases.json
python -X utf8 tests/run_regression.py --cases tests/regression_local/en_cases.json --write-expected
python -X utf8 tests/run_regression.py --cases tests/regression_local/review_cases.json --write-expected
```

当前基线：英文稿与综述均为防御性 20 PASS / 0 WARN / 0 FAIL、AI 结构 20 PASS、写作机检 14 PASS / 6 WARN / 0 FAIL。`CNKI_*` 规则只对中文生效，英文文本不套用知网句式阈值。

### 触发评测

```bash
python -X utf8 tests/evaluate_triggers.py          # 词法基线
python -X utf8 tests/evaluate_triggers.py --llm    # 用 DeepSeek 模拟宿主路由
```

`tests/trigger_cases.json` 含 15 条应触发、10 条不应触发。当前词法基线 25/25；LLM 模式触发 25/25、脚本路由 15/15。触发词与 description 改动后需同步用例。

## 维护

- 词库：改 `scripts/_lexicon.json`（中文 45 / 英文 78 条），无需改代码。
- 防御性规则：改 `scripts/defensive_patterns.json`（类别、正则、严重度、改法），再跑测试更新期望输出。
- 来源边界：`scripts/writing_lint.py`、`scripts/latex_clean.py` 及投稿信/审稿回复模板派生自 scipilot-writing-skill（MIT），本地已扩展 LaTeX 掩蔽；`check_defensive_writing.py`、`defensive_patterns.json`、`_kb.py`、`_rewrite.py` 为本项目自建。

## 结构

```text
paper-writing-assistant/
├── SKILL.md
├── README.md
├── LICENSE
├── lifecycle.yaml
├── agents/openai.yaml
├── config/defaults.json
├── templates/                 # 投稿信/审稿回复模板
├── assets/
│   ├── profiles/              # 章节模板与大纲 JSON
│   ├── styles/                # 改写风格指引
│   ├── corpus.example/        # 范文结构示例（不含第三方原文）
│   └── corpus/                # 个人范文（gitignore）
├── references/                # 写作规范、章节 playbook、期刊风格、去 AI 味手册
├── scripts/                   # 10 入口 + 共享模块 + 规则引擎 + 词库/防御性规则
└── tests/                     # 契约测试、期望输出、人工评测提示词
```

## 已知边界

- `lint_writing.py` 与 `check_defensive_writing.py` 是启发式检测：词表与正则只提示可能性，误报/漏报都存在，判定以整节或全文为准，最终由作者复核。
- `check_ai_style.py` 检测段落结构（模板网格、节奏、证据密度），不判断文本是否由 AI 生成；FAIL 只代表结构高度模板化。`CNKI_*` 规则来自公开视频的个人实测（2026-10-24 知网更新），是经验规则而非官方口径，不能用于规避检测。
- 防御性检测不判断“这条局限是否必须报告”。真实局限在讨论章保留一次是合规写作，`--section discussion` 会把自贬类降为 WARN。
- `rewrite_academic_text.py` 只保证不改动数值 token 并标出新增数值；语义等价、引用归属与单位一致性仍需人工核对。
- 默认面向方法-实验类论文；人文社科、纯综述使用时，把“指标、实验、对照”等规则改写为对应的论证单位（论点、材料、案例、比较对象）。
- 尚未实现全文级事实/一致性审计（跨章节数值、术语、研究目标与结论对应）；当前版本先保证单段与章节级检查的确定性。
- `latex_sanitize --fix` 已保护 `$$...$$`、数学环境、引用/URL 参数、表格 `&` 与 `verbatim`，但自动修复仍建议在版本控制下运行，先看 `diff`/`changes` 再采用。

## 许可

MIT，Copyright (c) 2026 sanqiuyef。

`scripts/writing_lint.py`、`scripts/latex_clean.py`、投稿信/审稿回复模板与深度润色工作流来自 [scipilot-writing-skill](https://github.com/Haojae/scipilot-writing-skill) v1.0.0（MIT，Copyright (c) 2026 Haojae）；第三方声明见 `LICENSE`。
