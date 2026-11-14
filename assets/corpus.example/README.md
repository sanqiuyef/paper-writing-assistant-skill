# 范文集结构示例

`assets/corpus/` 用于给 `rewrite_academic_text.py --corpus <name> --paper-type <type>` 提供 few-shot 范文。为避免再分发第三方论文原文，本仓库只附带一个自写示例（`cross-domain/general.json`），不包含真实文献摘录。

## 目录约定

```text
assets/corpus/<corpus>/<paper_type>.json
```

- `<corpus>`：`cross-domain` / `official-media` / `songbei` 等，`scripts/_common.py` 的 `CORPUS_NAMES` 需包含该名称。
- `<paper_type>`：`general` / `method-experiment` / `case-study` / `review`。

## JSON 结构

```json
{
  "paper_type": "general",
  "description": "说明",
  "source_base": "来源说明",
  "sections": {
    "introduction": [
      {"source": "作者 年份《标题》", "text": "段落原文", "note": "可模仿的写法"}
    ]
  }
}
```

`sections` 可用键：`introduction`、`method`、`experiment`、`discussion`。加载器只读 `text` 与 `source`。

## 使用自己的范文

```bash
mkdir -p assets/corpus/my-domain
cp assets/corpus.example/cross-domain/general.json assets/corpus/my-domain/general.json
# 编辑内容后：
python -X utf8 scripts/rewrite_academic_text.py --input-file draft.md --corpus my-domain --paper-type general
```

`assets/corpus/` 已在 `.gitignore` 中，个人范文不会被误提交。
