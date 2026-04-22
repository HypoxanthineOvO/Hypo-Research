# Targeted Search Skill

## 概述

此 Skill 用于辅助学术文献调研。
它通过 Query Expansion 提升文献召回率，并通过 Relevance Filtering 过滤噪声论文。
Python 工具层负责调用外部文献 API、去重、合并和写入本地结果；Query Expansion 与相关性判断由 Agent 自主完成。

## 工具清单

- `hypo-research search "<query>" [options]`
  单 query 检索。
- `hypo-research search "<query>" -eq "<variant1>" -eq "<variant2>" [options]`
  多 query 检索。
- `hypo-research search --queries-file <path> [options]`
  从 JSON 文件读取 query 列表和可选 expansion trace。

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
Step 2: 执行检索
  将原始 query + 所有变体传入 CLI，一次 multi_query_search 完成
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
  将最终结果和元数据写入 data/ 目录
  向用户汇报调研结果摘要
```

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

## 注意事项

- 不需要调用任何外部 LLM API，Agent 自身就是 LLM。
- 如果 Agent 判断 query 已经足够精确，可以跳过 expansion，直接使用单 query 检索。
- Relevance filtering 是可选的；对于小规模结果集（少于 20 篇），Agent 可以直接人工审阅。
