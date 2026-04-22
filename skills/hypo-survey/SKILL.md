---
name: hypo-survey
description: >
  Run a comprehensive multi-source literature survey. Searches Semantic Scholar,
  OpenAlex, and arXiv in parallel, deduplicates, cross-verifies, and generates
  a structured report with BibTeX references.
license: MIT
---

# /hypo-survey — 综合文献调研

执行一次完整的多源文献调研。

## 参数

$ARGUMENTS
- topic: 调研主题（必填）
- year_range: 年份范围（可选，默认近 5 年）
- sources: 数据源（可选，默认 all）
- output_name: 输出目录名（可选，自动生成）

## 工作流

1. 根据用户提供的 topic，设计 1 个主 query 和 2-3 个扩展 query
   - 主 query：直接对应 topic
   - 扩展 query：同义词、缩写、相关术语
   - 示例：topic="cryogenic computing for GPU"
     - 主 query: "cryogenic computing GPU"
     - 扩展: "cryo-CMOS processor", "low temperature VLSI"

2. 构造并执行命令：

```bash
uv run hypo-research search "<main query>" \
  -eq "<expanded 1>" \
  -eq "<expanded 2>" \
  --year-start <year_start> \
  --year-end <year_end> \
  --source <sources> \
  --output-dir data/surveys/<output_name>
```

3. 检索完成后：
   - 读取 `results.md`，向用户汇报摘要
   - 检查 auto-verify 输出，标记可疑论文
   - 提供 `references.bib` 路径供用户使用
   - 如果结果偏少（<10 篇），建议用户扩展 query 或放宽年份

4. 向用户输出完成报告：
   - 检索统计：X 篇论文（Y 已验证，Z 单源）
   - 关键发现：按 citation count 列出 Top 5
   - 数据质量：auto-verify 发现的问题数
   - 输出文件路径
