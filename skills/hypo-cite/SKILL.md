---
name: hypo-cite
description: >
  Expand a literature candidate pool by traversing the citation graph from seed
  papers. Uses Semantic Scholar and OpenAlex APIs to discover citing and cited
  papers, deduplicates, and outputs results compatible with /hypo-screen.
  Use this whenever the user wants to find papers connected to known seed
  papers, asks for citation-network expansion, or needs a Litmaps /
  Connected-Papers-style discovery step between survey and screening.
license: MIT
---

# /hypo-cite — 引文图扩展

从种子论文出发，通过引用 / 被引关系发现相关论文。输出与 `/hypo-survey` 格式兼容，可直接传给 `/hypo-screen` 做分类。

如果项目根目录存在 `.hypo-research.toml`，可复用其中的项目级路径约定和 API 相关默认配置。

## 参数

$ARGUMENTS
- seeds: 种子论文列表（必填，支持 DOI / arXiv ID / 论文标题）
- depth: 遍历深度（可选，默认 1，最大 2）
- direction: 遍历方向（可选，`citations` / `references` / `both`，默认 `both`）
- year_range: 年份过滤（可选）
- output_name: 输出目录名（可选）

## 工作流

1. 解析种子论文标识符
   - DOI：直接使用
   - arXiv ID：转换为 S2 格式 `ARXIV:xxxx`
   - 论文标题：通过 S2 Search API 查找匹配

2. 构造并执行命令：

```bash
uv run hypo-research cite \
  --seeds "<seed1>" "<seed2>" "<seed3>" \
  --depth <depth> \
  --direction <direction> \
  --year-start <year_start> \
  --year-end <year_end> \
  --output-dir data/citations/<output_name>
```

3. 遍历完成后：
   - 汇报发现的论文数量和来源分布
   - 列出高引用论文 Top 5
   - 如果有无法解析的种子，提醒用户
   - 建议用 `/hypo-screen` 对结果做分类

4. 向用户输出完成报告：
   - 种子论文：N 篇已解析（M 篇失败）
   - 扩展结果：X 篇（Y 来自 citations，Z 来自 references）
   - 去重统计：原始 A 篇 -> 去重后 B 篇
   - 输出文件路径
