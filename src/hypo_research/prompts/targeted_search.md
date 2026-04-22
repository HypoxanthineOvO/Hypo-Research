# Targeted Search Skill

## Skill Registration

This prompt is part of the Hypo-Research Skill.
- Project AGENTS.md: see `AGENTS.md` at project root for capability overview
- Skills: `skills/{survey,quick-search,review-results}/SKILL.md`
- Installer: `install-skills.sh`
- User guide: `docs/skill-usage-guide.md`

## 概述

此 Skill 用于辅助学术文献调研。
它通过 Query Expansion 提升文献召回率，通过多源并行检索提升覆盖度，并通过 Relevance Filtering 过滤噪声论文。
Python 工具层负责调用外部文献 API、去重、交叉验证和写入本地结果；Query Expansion 与相关性判断由 Agent 自主完成。

## 工具清单

- `hypo-research search "<query>" [options]`
  单 query 检索。
- `hypo-research search "<query>" -eq "<variant1>" -eq "<variant2>" [options]`
  多 query 检索。
- `hypo-research search --queries-file <path> [options]`
  从 JSON 文件读取 query 列表和可选 expansion trace。
- `--source / -s`
  选择数据源，可选 `s2`、`openalex`、`arxiv`、`all`。
- `--openalex-email`
  为 OpenAlex polite pool 提供 email，提高礼貌请求额度。
- `--no-hooks`
  禁用全部 hook，不生成 BibTeX、不生成 Markdown 报告，也不执行自动元数据检查。
- `--no-bib`
  仅禁用 BibTeX 输出。
- `--no-report`
  仅禁用 Markdown 报告输出。
- `--no-auto-verify`
  仅禁用自动元数据质量检查。

## 推荐工作流程

```text
用户提出研究问题
    ↓
Step 1: Query Expansion（Agent 自主完成）
  分析用户 query，生成 3-5 个变体，策略包括：
  - synonym: 用同义词/等价表达替换关键术语
  - abbreviation: 缩写与全称互换
  - cross-discipline: 用邻近学科的术语重新表述
  - specific: 聚焦到某个子方向
  - general: 扩大范围以捕获边缘相关论文
    ↓
Step 2: 多源并行检索
  默认使用全部源：
  - Semantic Scholar
  - OpenAlex
  - arXiv
  将原始 query + 所有变体传入 CLI，一次检索完成多 query + 多 source 合并
    ↓
Step 3: Relevance Filtering（Agent 自主完成）
  浏览返回的论文标题和摘要，为每篇评定相关性分数 (0-5)：
  - 5: 直接研究该主题
  - 4: 高度相关的近缘工作
  - 3: 中等相关，有关联但不直接
  - 2: 边缘相关
  - 1: 勉强相关
  - 0: 无关
  过滤掉低于阈值（默认 3）的论文
    ↓
Step 4: 输出整理
  搜索完成后自动输出：
  - results.json
  - meta.json
  - references.bib
  - results.md
  查看 auto-verify 产生的 warning / error
  对标记为 error 的论文谨慎对待
  向用户汇报调研结果摘要
```

## 多源说明

- Semantic Scholar:
  citation graph 强，引用关系和计数较好，综合覆盖广。
- OpenAlex:
  全学科覆盖较强，元数据丰富，适合补足非 CS 领域。
- arXiv:
  对 CS / Physics preprint 覆盖最好，适合捕捉最新预印本。

何时选择特定源：

- 只关注 preprint 时，可以优先 `--source arxiv`。
- 需要引用关系和 citation count 时，可以优先 `--source s2`。
- 默认建议使用全部源，交给工具层做跨源去重与交叉验证。

交叉验证含义：

- `verified`:
  至少 2 个源确认。
- `single_source`:
  仅 1 个源确认。
- Agent 可以优先信任 `verified` 论文，再补充评估 `single_source` 结果。

## queries-file 格式

Agent 可以生成如下 JSON 文件并传给 `--queries-file`：

```json
{
  "queries": ["original query", "variant 1", "variant 2"],
  "expansion_trace": {
    "original_query": "original query",
    "variants": [
      {"query": "variant 1", "strategy": "synonym", "rationale": "..."},
      {"query": "variant 2", "strategy": "cross-discipline", "rationale": "..."}
    ],
    "all_queries": ["original query", "variant 1", "variant 2"]
  }
}
```

## 输出文件说明

- `results.json`
  结构化结果，适合机器读取和后续脚本处理。
- `meta.json`
  检索元数据、source 统计、verification 统计、query expansion 记录。
- `references.bib`
  BibTeX 文件，可直接导入 LaTeX / Zotero 等文献工具。
- `results.md`
  人类可读的 Markdown 调研报告，便于快速审阅和分享。

## 注意事项

- 不需要调用任何外部 LLM API，Agent 自身就是 LLM。
- 如果 Agent 判断 query 已经足够精确，可以跳过 expansion，直接使用单 query 检索。
- Relevance filtering 是可选的；对于小规模结果集（少于 20 篇），Agent 可以直接人工审阅。
- 如果只想验证某一类来源，可以用 `--source` 控制检索范围。
- 默认启用 hook；如果只想拿原始 JSON 结果，可用 `--no-hooks`。
