# /review-results — 审查调研结果

审查已有的文献调研结果目录，提供分析和建议。

## 参数

$ARGUMENTS
- path: 调研结果目录路径（必填，如 `data/surveys/2026-04-22_cryogenic_gpu`）

## 工作流

1. 读取指定目录下的 `results.json` 和 `meta.json`
2. 分析结果：
   - 总论文数、已验证比例
   - 来源分布
   - 年份分布
   - auto-verify 问题汇总
3. 向用户提供：
   - 结果质量评估
   - 高引用 / 高相关论文推荐
   - 如果质量不理想，建议追加检索的 query
4. 如果用户需要，可以帮助筛选子集并生成新的 BibTeX
