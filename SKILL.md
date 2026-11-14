---
name: paper-writing-assistant
description: 中英文学术论文写作与润色助手（脚本版）：AI 词检查、模板/大纲、改写、写作机检、防御性写作检测、LaTeX 转义。语料可由 lancedb-search 或本地 Markdown/Obsidian 提供。触发：润色、polish、去 AI 味、查语言、填模板、生成大纲、写摘要/引言、翻译润色、cover letter、rebuttal、回复审稿意见、投稿前终检、事实核对、防御性写作、这段太像 AI 写的。
---

# Paper Writing Assistant

## 触发条件

当用户需要“写论文”“检查语言”“替换 AI 词”“填模板”“生成大纲”“润色/polish”“去 AI 味”“写 cover letter”“回复审稿意见/rebuttal”，或要求消除防御性写作、按发布会原则重排叙事时调用。

本 skill 的能力全部在 `scripts/` 下，按任务选一个或几个脚本；**推荐组合不是强制顺序**，可跳过不适用步骤。默认面向方法-实验类论文；人文社科、纯综述请把“指标、实验、对照”等规则改写为对应的论证单位（论点、材料、案例、比较对象）。

## 能力 → 脚本索引

所有脚本位于 `scripts/`，用同一解释器运行。默认命令前缀：

```bash
python -X utf8 scripts/<脚本名>.py
```

（要求 Python ≥ 3.10；Windows 控制台建议加 `-X utf8` 避免 GBK 乱码。）

通用约定：短文本用 `--text`，长文本用 `--input-file <路径>`（`-` 表示 stdin）；stdout 只输出一个 JSON 对象 `{"ok": true, "tool": "...", "data": {...}}`，诊断走 stderr。退出码：`0` 成功（lint/LaTeX/防御性检测另有 PASS）；`1` 门控不通过（lint=FAIL，latex=存在 FAIL，defensive=FAIL）；`2` 参数或输入错误；`3` 运行时错误（模板缺失、语料无命中、API key 缺失、外部调用失败）。

| 脚本 | 用途 | 关键参数 | 输出要点 |
|:---|:---|:---|:---|
| `check_academic_language.py` | 语料级 AI 标记词检查，给替换建议 | `--text`/`--input-file`、`--language auto/zh/en` | `data.status`（clean/issues_found）、`data.findings[]`（pattern/context/position） |
| `check_ai_style.py` | 结构级 AI 风格检测：模板腔、节奏均质、证据密度、连接词堆叠、AI 词密度、知网句式（动宾+“了”、`A的B与C`、形容词+名词重复、长句）；`--report` 导出段落骨架 HTML | `--text`/`--input-file`、`--language`、`--report` | `data.verdict`、`metrics`、`issues[]`、`report_path`；FAIL=模板网格，其余多为 WARN/INFO |
| `replace_ai_phrases.py` | AI 腔用词检测；`--apply` 时插入 `[[建议]]` 占位符 | `--text`/`--input-file`、`--language`、`--apply` | `data.details[]`、`data.result_text`；默认 dry-run |
| `fill_section_template.py` | 取章节/投稿信/审稿回复模板，注入 `{{占位符}}` | `--section`、`--params`/`--params-file`、`--language`、`--paper-type`、`--profile` | `data.template`、`data.template_id`、`data.evidence_basis` |
| `generate_outline.py` | 生成章节结构与配图方案 | `--language`、`--paper-type`、`--profile` | `data.sections[]`、`data.figures[]` |
| `rewrite_academic_text.py` | DeepSeek 降 AI 味改写，带数字编造防线；`--dry-run` 只组装提示词、不发请求 | `--text`/`--input-file`、`--style`、`--language`、`--reference-texts`/`--reference-file`、`--corpus`、`--kb`、`--kb-dir`、`--temperature`、`--dry-run` | `data.rewritten`、`changes`、`preserved_facts`、`risks`；`--dry-run` 返回 `system_prompt`/`user_prompt`；在线调用需 `DEEPSEEK_API_KEY` |
| `fact_integrity_check.py` | 对比原文/改写稿的数值、单位、引用、术语与结论方向 | `--original`、`--revised`、`--terms`/`--terms-file`、`--bracket-citations`、`--no-directions` | `data.verdict`、`issues[]`（缺失/新增/单位变化/方向反转）；**退出码 1 = FAIL** |
| `lint_writing.py` | 确定性写作质量门控，返回 PASS/WARN/FAIL | `--text`/`--input-file`、`--mode plain/word/docx/markdown/latex`、`--language` | `data.verdict`、`fail/warn/info`、`issues[]`；**退出码 1 = FAIL，不是执行失败** |
| `check_defensive_writing.py` | 防御性写作检测：自贬、叠甲、预演质疑、过程汇报、括号摊底、叠层模糊、边界重复、反向夸大 | `--text`/`--input-file`、`--section body/abstract/introduction/results/discussion/conclusion`、`--strict` | `data.verdict`、`issues[]`（severity/code/line/count/examples/suggestion）；**退出码 1 = FAIL** |
| `latex_sanitize.py` | LaTeX 转义体检；`--fix` 返回修复稿 | `--text`/`--input-file`、`--fix` | `data.problems[]`（severity/message）、`fixed_text`、`changed` |

常用示例：

```bash
# 1) 先看 AI 词，不改原文
python -X utf8 scripts/check_academic_language.py --input-file 第3节.md

# 2) 取章节模板
python -X utf8 scripts/fill_section_template.py --section abstract --paper-type general

# 3) 机检门控（FAIL 必修）
python -X utf8 scripts/lint_writing.py --input-file 第3节.md --mode word --language zh

# 4) LaTeX 体检并修复
python -X utf8 scripts/latex_sanitize.py --input-file draft.tex --fix

# 5) 降 AI 味：先看结构，再取范文改写
python -X utf8 scripts/check_ai_style.py --input-file 第3节.md --report 骨架报告.html
python -X utf8 scripts/rewrite_academic_text.py --input-file 第3节.md --style academic --kb zh --reference-file 范文片段.md

# 5b) 不外发：只组装提示词，交给宿主 agent 改写
python -X utf8 scripts/rewrite_academic_text.py --input-file 第3节.md --dry-run

# 5c) 事实核对：数值/单位/引用/术语/结论方向
python -X utf8 scripts/fact_integrity_check.py --original 第3节_原稿.md --revised 第3节_改稿.md --terms KAN-PC

# 6) 防御性写作检测（摘要/结论建议加 --section；终稿可加 --strict）
python -X utf8 scripts/check_defensive_writing.py --input-file 第3节.md --section results
```

脚本之间没有隐式状态：每个脚本单独起进程、单独输出 JSON。需要组合时由 agent 自己串联，例如“先 lint 定位问题段 → 再 rewrite 该段 → 再 lint 复检”。

## 任务 → 推荐脚本组合

| 任务 | 推荐组合（可增减） |
|:---|:---|
| 中文段落润色 | `lint_writing` 定位问题 → agent 改写 → `check_academic_language` 查 AI 词 → `lint_writing` 复检 |
| 英文润色 / 中译英 | `lint_writing --mode latex`（若为 LaTeX）→ agent 改写 → `latex_sanitize --fix` → 复检 |
| 降 AI 味 | `check_ai_style` 看结构问题 → `rewrite_academic_text --kb zh`（或 `--reference-file` 传 lancedb 命中段落）→ `fact_integrity_check` 核对数字/引用 → agent 按 `changes/risks` 复核 → `lint_writing` |
| 防御性写作清理 | `check_defensive_writing --section` 定位 → agent 按 `suggestion` 逐条改写（真实边界保留一次）→ 复检；摘要/结论必跑 |
| 写某章节 | `generate_outline` 取结构 → `fill_section_template --section` 取骨架 → agent 起草 → 机检 |
| 投稿信 / 审稿回复 | `fill_section_template --section cover_letter/rebuttal` → agent 填充 → `lint_writing` |
| 投稿前语言终检 | `lint_writing` → `latex_sanitize`（LaTeX）/ Word 纯文本检查 → 人工确认项清单 |

## 深度润色工作流

```
Stage 0 问询 → 起草/改写 → 机检门控 → AI 读稿自审（≤3 轮）→ 三段式交付
```

### Stage 0：信息收集（按任务定深度）

**Quick Mode（默认，段落/句子级）**：能从上下文推断的直接推断；有默认值的说明默认值后直接开始；只问真正影响结果的歧义（载体、语言方向），一次最多一个问题。适合“帮我润色这段”“这段太像 AI 写的”“查一下 LaTeX 转义”。

**Deep Mode（整章/投稿前）**：收齐下列 A-F，复述参数后等“开始”。适用于全文润色、投稿前终检、rebuttal 与 cover letter。

- **A 任务类型**：润色 / 翻译润色 / 缩写 / 扩写 / 去 AI 味 / 逻辑检查 / 写某章节 / 图表标题 / 审稿自检 / cover letter / rebuttal
- **B 文本载体**：`.tex`（LaTeX 纯净+转义规则） / `.docx`/Word（纯文本+全角标点+零 Markdown） / `.md` / 粘贴片段（问清最终落点）
- **C 目标期刊/会议**：决定结构、篇幅、风格；没有目标刊时给默认并说明
- **D 语言方向**：中→英 / 英→中 / 英→英 / 中→中
- **E 修改保守度**：默认“中等—宁缺毋滥”；可选“仅纠错”/“中等润色”/“深度重写”
- **F 参数复述确认**：收齐后复述全部参数，等用户“开始”信号再动笔

### 机检门控（必做）

改写完成后**必须**运行 `lint_writing.py`，并运行 `check_defensive_writing.py`：

- `data.verdict=FAIL`（退出码 1）→ 必须修复后复检，不得假装通过、不得伪造检查结果
- `data.verdict=WARN` → 逐项评估，决定是否回改
- **防御性检测**：摘要、引言、结论**必跑**；正文其他章节在涉及局限、对比或负结果时跑。FAIL 级（自贬、否定叠甲、预演质疑、叠层模糊、摘要/结论开头自贬）必须改；WARN 级（过程汇报、括号摊底、第一人称、边界重复、反向夸大）逐条判断
- **事实核对**：只要有原文/改稿对，必须跑 `fact_integrity_check.py --original 原稿 --revised 改稿`；数值缺失/新增、单位变化、引用增减、结论方向反转均为 FAIL，必须回改；数值顺序变化为 WARN，核对指代是否受影响
- **结构风格（可选）**：被指“读着像 AI/模板腔”或改写前，跑 `check_ai_style.py` 看段落结构；`AI_TEMPLATE_GRID`（连续序数开头 + 句数一致）为 FAIL，必须重排段落；`AI_UNIFORM_RHYTHM`/`AI_LOW_SPECIFICITY`/`CNKI_*` 为 WARN，结合证据判断；AI 词密度仅 INFO。知网句式规则是经验规则、非官方口径，不能用来规避检测
- 同一轮依次跑 `check_academic_language.py` 做语料级 AI 词检查；LaTeX 载体加 `latex_sanitize.py --fix`
- 门控结论以整节或全文为准：`lint_writing` 按密度判定，几百字片段里一两处符号就可能越线
- 防御性检测只报不改：真实边界按证据保留一次并正面表述，删除防御不得反向升级为“首次/唯一/全面领先”

### AI 读稿自审（机器查不出的，靠读，最多 3 轮）

以审稿人视角重读改后文本：①逻辑是否连贯、有无跳跃或自相矛盾 ②是否 overclaim、是否把相关说成因果 ③是否仍有“读着像 AI”的段落 ④术语/缩写/时态是否前后一致 ⑤是否偏离原意或动了不该动的事实 ⑥是否有只防质疑、不推进论证的防御性句子（逐句过删除检验：无损失即删；必要边界声明保留一次且正面表述）⑦叙事是否为工作汇报式、是否把不占优指标设成了主战场、摘要前五句有无问题与贡献、结论有无突然的自我否定（发布会原则 8 问）。发现问题 → 回改 → 重跑机检。3 轮仍有残留则如实标注“建议人工确认项”交付，不假装完美。

### 三段式交付（透明可溯）

- **Part 1**：改后文本（LaTeX 守纯净与转义；Word/中文纯文本、全角标点、零 Markdown）
- **Part 2**：直译/回译核对（翻译类任务必附，供核对未走样）
- **Part 3**：修改日志（改了什么、为什么）

Quick Mode 可只交 Part 1 + 一句话改动摘要；Deep Mode 三段齐全。脚本只能产出机检 JSON；Part 2 与 Part 3 必须由 agent 生成，不得用“已跑脚本”代替。

## 铁律（任何输出必须满足）

1. **诚信**：润色只动表达，绝不改动任何数据、数值、方向、结论或实验事实；绝不编造文献、结果、引用（找文献用可用的检索工具，如 lancedb-search / zotero / elsevier；查不到标【待补证】而不是硬编）
2. **宁缺毋滥**：原文若已清晰、准确、规范，保留原样并明确肯定，不为追求形式变化强行换词
3. **断言=证据**：hedging 与 boosting 强度必须匹配证据强度，绝不 overclaim
4. **载体纯净**：Word 端零 Markdown；LaTeX 端特殊字符转义、保留 `\cite{}`/`\ref{}` 等命令
5. **透明可溯**：绝不静默重写，按三段式交付
6. **机检不造假**：机检 FAIL 不得假装通过
7. **叙事不越证据**：发布会原则只调整叙事重心与表达，不得删除或隐瞒不利结果与关键对照，不得改口径、指标定义或比较对象，不得把“相关”写成“导致”以换取更强叙事

## 叙事层：发布会原则（反防御性写作）

论文是一场学术发布会，不是项目总结、实验日志或自我审查报告。先识别这项工作最值得发表的价值，再围绕它组织全部材料。完整规则、决策优先级与快速提示词见 `references/anti_defensive_writing.md`。

**执行顺序**：先过「证据边界」（必须报告的不利结果、关键对照与影响结论的局限），再按叙事规则调整；叙事规则不得压掉证据边界。真实局限在讨论章保留一次是合规写作，不属于防御性缺陷；`check_defensive_writing.py --section discussion` 对自贬类只报 WARN，由作者判断。

**叙事**

1. 只围绕证据能牢固支撑的优势组织主线，不构成优势的内容不进主线。
2. 不写“先做了什么、后来试了什么、哪些失败”的过程；只保留最终成立的逻辑：问题为什么重要 → 现有方法为什么不够 → 本文提出了什么 → 证据如何支持。
3. 不占优的指标不设为主战场：换用能反映本文价值的评价维度、场景或口径，并明确本文赢的是哪一场比较。
4. 优势主动说明：在什么条件下最好、为什么会出现、解决了什么实际问题，不指望审稿人从表格里自己发现。
5. 比较范围与主张强度一致：只提出证据能支撑的主张，不追求“所有指标全面领先”。

**语言**

- 禁自我削弱式表述：“遗憾的是”“仅是”“仍明显落后”“效果有限”“存在严重不足”。
- 不占优的结果不说输：是否必须讨论 → 能否由目标差异、约束或场景解释 → 是否体现合理权衡 → 能否收缩主张避免正面对撞 → 是否调整主线使其不再承担核心证明。
- 不把局部现象上升为对整体方法的否定，不替审稿人代写弱点。

**实验**

每个实验承担一个论证职责：证明方法有效 / 证明优势来自关键机制 / 证明目标场景价值 / 排除最可能的替代解释。不承担职责的实验删除、弱化、移入附录或重新设计。

**结构**

- 摘要与引言：重要且未解决的问题 → 现有方法的关键缺口 → 本文思路 → 最硬的结果与意义；不从实现细节和过程开始，不在贡献建立前讨论不足。
- 结论只强化记忆点：解决了什么、提出了什么、证明了什么、为什么重要；末段不突然自我否定、不扩大局限。

**不理想材料的处理优先级**

删除无关内容 → 缩小主张 → 换有证据支撑的评价维度 → 解释为目标差异或合理权衡 → 重组实验 → 重新定义故事 → 无法回避且影响核心结论时才做必要说明。

**证据边界（不得越过）**

- 已执行的关键对照、不利结果、失败实验不得删除或隐瞒；只能如实报告并重新定位其叙事位置。
- 不得为“不设比赛”修改数据、口径、指标定义或比较对象；换维度须有该维度的真实结果支撑。
- 不得用发布会原则洗掉真实局限；必要边界仍按铁律只写一次、正面表述。

**交稿自查（8 问）**

①这句话是否无意扩大了本文要承担的责任？②是否回答了一个没人问的问题？③是否把局部现象写成普遍缺陷？④是否用了比证据更宽的负面判断？⑤是否在按“我们做了什么”的过程展开？⑥是否把不领先的指标设成了主战场？⑦摘要前五句里问题和贡献都出来了吗？⑧结论里有没有突然的自我否定？

## 载体规范

- **LaTeX**：正文特殊字符 `% & # _` 转义；保留 `\cite{}`/`\ref{}`/`\label{}`；数学环境 `$...$` 原样；不改命令参数内的下划线。
- **Word/docx**：纯文本、全角标点、零 Markdown（`**`、`` ` ``、`#`、列表符）；`lint_writing --mode word` 会以 FAIL 拦截 Markdown 残留。
- **Markdown**：保留结构与上标公式；`lint_writing --mode markdown` 目前与 `plain` 同规则，不额外放宽。

## 章节名与模板参数

| 参数 | 中文 | English |
|:---|:---|:---|
| abstract | 摘要 | Abstract |
| introduction | 引言 | Introduction |
| related_work | 相关研究 | Related Work |
| method | 研究方法 | Methodology |
| experiment | 实验设计 | Experimental Design |
| result | 结果与分析 | Results and Analysis |
| discussion | 讨论 | Discussion |
| conclusion | 结论 | Conclusion |
| cover_letter / rebuttal | 投稿信 / 审稿回复 | Cover Letter / Rebuttal |

`--paper-type`：`general` / `method-experiment` / `case-study` / `review`；`--profile <name>` 读取 `assets/profiles/<name>/` 下的自定义章节标题与大纲（项目专用 profile 默认不随仓库分发，可自行添加）。`{{占位符}}` 只替换双花括号；profile 模板中的单花括号占位符保持原样。

## 数据与语料来源

- **证据级检索（优先，若环境提供）**：`lancedb-search` MCP 的 `search_knowledge(query, search_mode="hybrid")` 取原文片段，`get_document(filepath)` 取全文；把命中段落写成文件后用 `rewrite_academic_text.py --reference-file` 传入，或在正文中按引用规范转述。
- **离线语料（支撑）**：本地 Markdown/Obsidian 语料目录，由 `_kb.py` 做零依赖关键词检索；用 `--kb-dir` 或 `PWA_KB_DIR` / `PWA_VAULT_DIR` 指定根目录（也可写在 `config/defaults.json` 的 `vault_dir`），`--kb zh/en` 按段落语言过滤，`--kb <主题目录>` 限定范围。
- **skill 自带资产**：`templates/`（投稿信/审稿回复）、`assets/profiles/`（章节模板与大纲 JSON）、`assets/styles/`（改写风格指引）、`assets/corpus.example/`（范文 JSON 结构示例）。自己的范文放 `assets/corpus/`（不入库），语料全文不随 skill 分发。
- **外发边界**：`rewrite_academic_text.py` 不经 `--dry-run` 时会把正文、范文与检索片段发送到配置的 DeepSeek 端点。未发表数据、审稿材料、保密内容必须先取得作者同意；不外发时用 `--dry-run`，由宿主 agent 本地改写。

## 参考文档（references/，按需加载，勿全文塞进回复）

| 文件 | 内容 |
|:----|:----|
| `references/de_ai_humanize.md` | AI 指纹识别清单 + 中英改写原则 + 留人味 |
| `references/section_playbooks.md` | 逐章节写法（Title/Abstract/Introduction-CARS/Methods/Results/Discussion/Conclusion） |
| `references/sci_writing_principles.md` | 时态/语态/hedging/衔接/数字单位统计规范 |
| `references/journal_styles.md` | Nature/Science/IEEE/中文核心等期刊风格路由 |
| `references/prompt_library.md` | 18 个写作任务剧本（翻译/润色/缩写/扩写/实验分析/caption 等） |
| `references/anti_defensive_writing.md` | 发布会原则完整版（叙事/语言/实验/结构/决策优先级/证据边界/快速提示词） |
| `references/cnki_aigc_patterns.md` | 知网 2026-10 更新后的句式经验（动宾+“了”扎堆、`A的B与C` 名词串、形容词+名词重复、长句），含改写示例与误判边界 |

## 工程化文件

- `README.md`：面向人的安装、用法、退出码与维护说明。
- `config/defaults.json`：语料根目录、DeepSeek 端点/模型/超时；同名环境变量优先。
- `templates/`：投稿信/审稿回复模板（运行时读取）；`assets/` 放章节模板、profile 大纲、风格与范文。
- `tests/`：`python -m unittest discover -s tests -v` 跑契约测试；`tests/run_regression.py` 跑合成回归；`tests/build_regression_local.py` 从本地真实稿件生成 gitignored 回归集；`tests/evaluate_triggers.py --llm` 评测触发与脚本路由。有意改行为后先跑 `tests/update_expected.py`。
- `agents/openai.yaml`、`lifecycle.yaml`：可选平台元数据，ZCode 忽略；发布到其他平台时按目标 schema 调整。

## 脚本维护

- `scripts/writing_lint.py`、`scripts/latex_clean.py` 为规则引擎（自 scipilot-writing-skill v1.0.0 融合，MIT License），一般不改；改规则需同步 `scripts/` 内两份副本的行为说明。
- `scripts/_lexicon.json` 为替换词库（中文 45 条 / 英文 78 条），由原实现导出；增删词条后直接改 JSON，不需改代码。
- `scripts/defensive_patterns.json` 为防御性写作规则（类别、正则、严重度、改法）；增删模式后同步 `tests/expected_outputs/defensive_*`。
- `scripts/_common.py` 集中路径、语言判定、模板路由与数字防线；`scripts/_kb.py` 语料检索；`scripts/_rewrite.py` 提示词组装与 DeepSeek 调用。

## Credits

- `writing_lint.py`、`latex_clean.py`、cover_letter/rebuttal 模板与深度润色工作流，自 **scipilot-writing-skill** v1.0.0 融合引入（MIT License, Copyright (c) 2026 Haojae）
- 上游仓库：https://github.com/Haojae/scipilot-writing-skill
- 本 skill 其余部分（语料词库、模板、DeepSeek 改写层、大纲）为自制；2026-11 由 MCP 服务重构为脚本版
