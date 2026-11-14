# Paper Writing Assistant

中英文论文写作、润色、机检与降 AI 味的本地 Agent Skill。能力全部落在 `scripts/`，按需单独调用，不依赖 MCP 进程。

## 能力

| 脚本 | 用途 |
|:---|:---|
| `check_academic_language.py` | 语料级 AI 标记词检查，给替换建议 |
| `replace_ai_phrases.py` | AI 腔用词检测；`--apply` 插入 `[[建议]]` 占位符 |
| `fill_section_template.py` | 章节 / 投稿信 / 审稿回复模板，支持 `{{占位符}}` |
| `generate_outline.py` | 论文大纲与配图方案 |
| `rewrite_academic_text.py` | DeepSeek 降 AI 味改写，带数字编造防线；`--dry-run` 只组装提示词、不发请求 |
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

# 5) 降 AI 味
python -X utf8 scripts/rewrite_academic_text.py --input-file section3.md --style academic --kb zh

# 5b) 不外发：只组装提示词，交给宿主 agent 改写
python -X utf8 scripts/rewrite_academic_text.py --input-file section3.md --dry-run

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

## 测试

```bash
python -X utf8 -m unittest discover -s tests -v
```

覆盖 8 个入口、固定输出对照、退出码 1/2/3、结构检查与 MCP 独立性。有意改行为后先运行：

```bash
python -X utf8 tests/update_expected.py
```

`tests/test_prompts.md` 提供 4 条人工评测提示词。

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
├── scripts/                   # 8 入口 + 共享模块 + 规则引擎 + 词库/防御性规则
└── tests/                     # 契约测试、期望输出、人工评测提示词
```

## 已知边界

- `lint_writing.py` 与 `check_defensive_writing.py` 是启发式检测：词表与正则只提示可能性，误报/漏报都存在，判定以整节或全文为准，最终由作者复核。
- 防御性检测不判断“这条局限是否必须报告”。真实局限在讨论章保留一次是合规写作，`--section discussion` 会把自贬类降为 WARN。
- `rewrite_academic_text.py` 只保证不改动数值 token 并标出新增数值；语义等价、引用归属与单位一致性仍需人工核对。
- 尚未实现全文级事实/一致性审计（跨章节数值、术语、研究目标与结论对应）；当前版本先保证单段与章节级检查的确定性。

## 许可

MIT，Copyright (c) 2026 sanqiuyef。

`scripts/writing_lint.py`、`scripts/latex_clean.py`、投稿信/审稿回复模板与深度润色工作流来自 [scipilot-writing-skill](https://github.com/Haojae/scipilot-writing-skill) v1.0.0（MIT，Copyright (c) 2026 Haojae）；第三方声明见 `LICENSE`。
