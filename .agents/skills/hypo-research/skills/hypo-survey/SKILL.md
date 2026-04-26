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

如果项目根目录存在 `.hypo-research.toml`，优先读取其中的 `survey` 默认配置（如 `default_topic`、`max_results`、`sources`）。

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

## 论文展示规则

在向用户展示 survey 结果时，对每篇论文：

1. 显示基本元数据（标题、作者、年份、场地、被引数）
2. 读取 `abstract` 字段，用 1-2 句中文概括论文的核心贡献和方法
3. 概括应突出：做了什么、怎么做的、主要结果
4. 专业术语保留英文（如 FHE、NTT、bootstrapping）
5. 如果 `abstract` 为空，标注“（无摘要）”

示例输出格式：

```text
📄 CryptoNAS: Private Inference on a Budget (ICLR 2024, 被引 45)
   → 提出针对 FHE 推理场景的神经架构搜索方法，通过联合优化
     FHE 友好算子和网络结构，在保持精度的同时将推理延迟降低 3×。
```

中文概括由 Agent 在交互时实时生成，不写入报告文件。`results.md`
保留英文 abstract 原文，`results.json` 保留完整 abstract 字段。
