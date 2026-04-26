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

## 论文打分规则

在获取 survey 结果后，你需要为每篇论文打两个分数（1-10 分），并在向用户
展示时简要说明评分理由（1 句话）。

### 综合评分（overall_score）

综合考虑以下因素：

- 与查询主题的相关性（40%）
- 论文的学术影响力：引用数、venue 档次（30%）
- 方法/贡献的新颖性和重要性（20%）
- 时效性：较新的论文适当加分（10%）

### 相关性评分（relevance_score）

纯粹评估与用户查询主题的相关程度：

- 10：直接解决用户查询的核心问题
- 7-9：高度相关，解决相关子问题或提供关键技术
- 4-6：中等相关，有参考价值但不是核心
- 1-3：边缘相关，仅在某个方面有联系

## 多维排序展示

向用户展示 survey 结果时，按以下结构呈现：

1. **📊 综合排序**（默认视图）— 按你的综合评分排序
2. **📈 引用数排序** — 按被引数降序
3. **🎯 相关性排序** — 按你的相关性评分排序
4. **📅 时间线** — 按年份分组，展示研究发展脉络

每篇论文旁标注它在其他视图中的排名，方便用户交叉参考。如果结果较少
（<5 篇），可以合并视图为一个表格。

示例：

```text
📊 综合排序：
1. [9.2] TFHE-rs (2022, 被引 180) — 📈#2 | 🎯#5
   → 用纯 Rust 实现了完整的 TFHE 库，支持多种参数集。
   评分理由：与 FHE 工程实现高度相关，引用和工具影响力都较强。
2. [8.7] CryptoNAS (2024, 被引 245) — 📈#1 | 🎯#1
   → 提出针对 FHE 推理的神经架构搜索方法。
   评分理由：直接面向 FHE private inference，方法贡献清晰且影响力高。
```
