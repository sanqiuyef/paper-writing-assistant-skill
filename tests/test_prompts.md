# 手动评测提示词

自动化契约测试只覆盖确定性输出；下面 3 条用于人工看 skill 的触发与工作流是否符合预期。每条都在新会话里直接发给 agent，不强制点名 skill。

1. **中文核心期刊润色（Word）**
   “帮我润色这一节到《水利学报》的语言风格，Word 投稿，保守改，不许动数字和引用。”
   预期：先问载体/期刊/保守度；`check_academic_language` → 改写 → `lint_writing --mode word`；交付三段式。

2. **降 AI 味（保留数据）**
   “这段读起来太像 AI 写的，帮我去掉 AI 味，但所有数值、单位、引用一个都不能动。”
   预期：`rewrite_academic_text`（可加 `--kb zh` 或 `--reference-file`）；核对 `changes/risks`；复跑 `lint_writing`。

3. **LaTeX 体检**
   “这段 LaTeX 有没有未转义的 % 和 &？有就修一下，数学公式别动。”
   预期：`latex_sanitize --fix`；说明 `fixed_text` 与 `changed`；不碰 `$...$`。

失败模式检查：若 agent 跳过机检、直接整段重写、改动数值或引用、把脚本输出当最终交付而不写修改日志，均视为不合格。
