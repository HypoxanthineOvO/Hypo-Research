# Literature Search And Citation Modules

## 职责

文献模块负责多源检索、query expansion 后的顺序聚合、引用/被引图扩展、去重、验证和结果输出。

## 主要文件

- `survey/targeted.py`：`TargetedSearch`，支持单 query、多 query、进度输出、hook 调用和结果落盘。
- `cite/traversal.py`：从 seed paper 沿 citation/reference relationship 扩展候选池。
- `hooks/`：搜索阶段后自动生成 BibTeX、Markdown 报告和元数据验证。
- `output/json_output.py`、`output/markdown_report.py`、`output/bibtex.py`：持久化检索结果和报告。
- `output/ranking.py`、`output/summary.py`：排序和摘要辅助。

## 数据流

用户 query 经 CLI 参数规范化为 `SearchParams`，由 source adapter 并发或顺序查询外部服务，结果转换为 `PaperResult`。随后经过 hook、dedup、verification 和 output 阶段，最终写入 JSON、Markdown 和 BibTeX 等结构化结果。

## 设计约束

外部服务失败应局部降级并记录 source count，不应让单个 source 默认终止整个多源检索。输出层不应重新发起检索请求。
