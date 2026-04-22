# Hypo-Research 使用指南

## 环境要求

本项目强制使用 [uv](https://github.com/astral-sh/uv) 管理环境和依赖，不使用 pip / virtualenv / conda。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/HypoxanthineOvO/Hypo-Research.git
cd Hypo-Research
uv sync
./install-skills.sh
```

## Skills

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `/hypo-survey` | 综合文献调研 | 发散式扩池，尽可能做大候选集 |
| `/hypo-cite` | 引文图扩展 | 从已知核心论文沿引用 / 被引关系发现相关工作 |
| `/hypo-screen` | 文献筛选分类 | 按自定义规则收敛、分类、出分析报告 |
| `/hypo-search` | 快速文献检索 | 单次点查、补检、精确查找 |
| `/hypo-lint` | LaTeX 结构检查 | 检查 label / ref / float / BibTeX 结构问题并辅助修复 |
| `/hypo-verify` | 引用验证 | 联网验证 `.bib` 引用是否真实存在并检查元数据错误 |

## 在 Claude Code 中使用

- `/hypo-survey topic="cryogenic computing for GPU" year_range=2020-2026`
- `/hypo-cite seeds="Cinnamon, CraterLake, F1" depth=1 direction=both`
- `/hypo-screen path="data/surveys/2026-04-22_cryo_gpu/" rules="A: cryo-CMOS; B: superconducting control"`
- `/hypo-search query="TFHE bootstrapping accelerator"`
- `/hypo-lint path="docs/" fix=true`
- `/hypo-verify bib="refs.bib" tex="docs/"`

## 在 Codex CLI 中使用

执行 `./install-skills.sh` 后，可直接使用：

- `/hypo-survey` 或 `/prompts:hypo-survey`
- `/hypo-cite` 或 `/prompts:hypo-cite`
- `/hypo-screen` 或 `/prompts:hypo-screen`
- `/hypo-search` 或 `/prompts:hypo-search`
- `/hypo-lint` 或 `/prompts:hypo-lint`
- `/hypo-verify` 或 `/prompts:hypo-verify`

也可以直接用自然语言描述需求，让 Agent 结合 `AGENTS.md` 自动路由。

## 典型工作流

1. 用 `/hypo-survey` 对主题做多 query、多源并行检索，建立候选池。
2. 用 `/hypo-cite` 从已知核心论文沿引用图扩展候选池。
3. 用 `/hypo-screen` 按你的分类规则收敛结果，并检查 recall checklist。
4. 用 `/hypo-search` 对薄弱方向做补充点查。
5. 重新筛选，输出最终分类报告和 BibTeX。
6. 写作阶段用 `/hypo-lint` 对 LaTeX 结构做静态检查和规范化修复。
7. 定稿前用 `/hypo-verify` 联网检查 `.bib` 是否混入幻觉论文或错误年份/DOI。

## 输出文件

- `results.json`：结构化论文列表
- `meta.json`：检索元数据和统计
- `references.bib`：BibTeX 引用文件
- `results.md`：人类可读调研报告
- `classified_papers.json`：筛选分类结果
- `analysis_report.md`：分类分析报告

## 配置 Semantic Scholar API Key（可选）

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key-here"
```

申请地址：https://www.semanticscholar.org/product/api#api-key-form

不设置时仍可使用，但大批量搜索可能触发 rate limit。
