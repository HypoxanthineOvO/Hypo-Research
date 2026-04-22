---
name: hypo-screen
description: >
  Screen and classify papers from a Hypo-Research survey output directory using
  user-defined rules. Generates a classification report with per-paper labels,
  category counts, and an analysis summary.
license: MIT
---

# /hypo-screen — 文献筛选分类

对已有调研结果按自定义规则进行筛选、分类、分析。将候选论文池收敛为结构化的分类报告。

## 参数

$ARGUMENTS
- path: 调研结果目录路径（必填，如 `data/surveys/2026-04-22_fhe_hw/`）
- rules: 分类规则（必填，自然语言描述各类别的定义）
- recall_checklist: 已知重要论文列表（可选，用于检查是否漏掉关键论文）
- output_name: 分类报告输出名（可选，默认 `classified`）

## 规则格式

分类规则用自然语言定义，每行一个类别，格式为 `类别名: 定义`。

示例：

```text
A: FHE + 大模型推理 + 硬件加速器（ASIC/FPGA/GPU）
B: FHE + 硬件加速器（CNN 或更小规模模型）
C: FHE + 大模型推理（纯软件优化）
D: CIM/PIM + FHE
排除: MPC/GC/OT 为主导方案（非纯 FHE）
```

## 工作流

1. 读取 `path` 下的 `results.json`（或 `results.md`）中的论文列表
2. 对每篇论文，根据 title + abstract + venue 判断所属类别：
   - 逐篇标注类别标签
   - 如果无法判断，标为 `未分类`
   - 对可疑 / 边界论文给出简要理由
3. 如果提供了 `recall_checklist`：
   - 检查每篇 checklist 论文是否在结果中
   - 对未命中的论文，用标题精确搜索补全
   - 报告 recall 统计（如 24/24 命中）
4. 生成分类报告：
   - `classified_papers.json`: 每篇论文含 `{title, authors, year, venue, doi, category, reason}`
   - `analysis_report.md`: 含分类计数、关键发现、类别概览、建议
   - 更新 `references.bib`: 标注类别
5. 向用户输出：
   - 分类计数表（如 A=2, B=26, C=17, D=9, 排除=7）
   - 每类的代表性论文（Top 3 by citations）
   - Recall checklist 命中率
   - 数据质量评估（单源论文占比、可疑标记数）
   - 建议后续操作（是否需要补充搜索特定方向）
