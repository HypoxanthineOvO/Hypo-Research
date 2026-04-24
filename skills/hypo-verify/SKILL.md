---
name: hypo-verify
description: >
  Verify whether BibTeX references are real and whether their metadata is
  correct. Use this whenever the user wants to validate a .bib file, detect
  hallucinated references, check DOI/title/year/venue/author consistency, or
  confirm that cited papers actually exist on Semantic Scholar and OpenAlex.
  Run the verification script first to collect objective metadata evidence, then
  let the Agent judge whether citation context in the .tex file accurately
  describes the paper.
license: MIT
---

# /hypo-verify — 引用验证

脚本负责联网核验引用是否存在、元数据是否匹配；Agent 负责解释 mismatch / not_found 的含义，并在提供 `.tex` 路径时判断引用上下文是否准确。

## 参数

$ARGUMENTS
- bib: `.bib` 文件路径（必填）
- tex: `.tex` 文件或目录（可选，只验证被引用的条目）
- project_dir: 显式项目根目录（可选，可自动发现主文件和 `.bib`）
- keys: 只验证指定 cite key（可选，逗号分隔）
- fix: 是否自动修复可修复项（可选，布尔值）

## 工作流

1. 运行验证脚本：

```bash
uv run hypo-research verify --stats <bib>
```

如果用户给了 `.tex` 路径或 key 过滤：

```bash
uv run hypo-research verify --stats <bib> --tex <tex> --keys <keys>
```

多文件项目可自动发现 `.bib`：

```bash
uv run hypo-research verify --stats --tex main.tex
uv run hypo-research verify --stats --project-dir ./paper
```

2. 解析 JSON 中的 `results`：
   - `verified`：记录为已确认，无需动作
   - `mismatch`：逐项检查 `mismatches`
   - `not_found`：高优先级警告，可能是幻觉论文
   - `error`：报告错误原因并建议补元数据

3. 如果提供了 `.tex` 路径：
   - 读取对应 `\cite{key}` 的上下文
   - 判断文字描述是否真的符合该论文内容
   - 这一步由 Agent 判断，不依赖脚本自动决策

4. 如果 `fix=true`：
   - 对年份 mismatch：可建议修改 `.bib` 中的 `year`
   - 对 verified 且本地缺 DOI：可补 `doi`
   - 对 `not_found`：不要自动删除，先提醒用户确认

5. 输出最终报告：
   - 验证摘要
   - mismatch / not_found / error 的详细问题
   - 如有 `.tex`，补充引用上下文判断

## 状态表

| 状态 | 含义 | Agent 行为 |
|------|------|------------|
| `verified` | API 确认论文存在且信息匹配 | 汇总列出，无需操作 |
| `mismatch` | 论文存在但某些字段不匹配 | 逐项检查，建议修正 |
| `not_found` | Semantic Scholar 和 OpenAlex 均未找到 | 高优先级警告，可能是幻觉论文 |
| `error` | API 错误或元数据不足 | 报告错误，建议补充元数据 |

## 输出要求

- 优先报告 `not_found` 和严重 `mismatch`。
- 对年份 mismatch，说明本地值和远程值。
- 对 venue mismatch，先判断是不是简称 vs 全称差异，避免误报。
- 如果用户想修 `.bib`，只自动改明确无争议的字段；不要擅自删除条目。
