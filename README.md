# 🔬 Hypo-Research

学术文献调研 AI Skill 包，在 Codex CLI 或 Claude Code 中一键调用，三源并行检索、自动去重验证、生成结构化报告。

## ✨ 特性

- **三源并行检索**：Semantic Scholar + OpenAlex + arXiv 同时搜索
- **自动去重 & 交叉验证**：DOI / 标题+作者 双重匹配，标记 verified / single-source / suspicious
- **筛选分类引擎**：按自定义规则对候选池分类，输出结构化分析报告
- **结构化输出**：Markdown 报告 + BibTeX 引用 + JSON 元数据
- **Skill 驱动**：通过 `/hypo-survey` 等命令直接调用，Agent 自动完成全流程

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/HypoxanthineOvO/Hypo-Research.git
cd Hypo-Research
uv sync
./install-skills.sh
```

> 没有 uv？`curl -LsSf https://astral.sh/uv/install.sh | sh`

### 配置（可选）

```bash
# Semantic Scholar API Key — 大幅提升搜索速率，不设置也能用
export SEMANTIC_SCHOLAR_API_KEY="your-key-here"

# 申请: https://www.semanticscholar.org/product/api#api-key-form
```

---

## 📖 Skills 使用指南

### `/hypo-survey` — 综合文献调研

完整的多源文献调研。Agent 自动设计查询、扩展关键词、三源并行检索、去重验证、生成报告。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `topic` | ✅ | 调研主题 | `"NeRF real-time rendering"` |
| `year_range` |  | 年份范围 | `2020-2026`（默认近 5 年） |
| `sources` |  | 数据源 | `all` / `s2` / `openalex` / `arxiv` |

**示例：**

```text
/hypo-survey topic="NeRF real-time rendering" year_range=2020-2026
```

Agent 会自动：
1. 设计主 query + 扩展 query：`"neural radiance field real-time"`、`"instant NGP"`、`"3D Gaussian splatting acceleration"`
2. 三源并行检索 -> 去重合并 -> 交叉验证
3. 输出报告：

```text
📊 检索完成

- 论文数：142（87 verified，55 single-source）
- Top 5：
  1. Instant-NGP (2022, SIGGRAPH, citations=1847)
  2. 3D Gaussian Splatting (2023, SIGGRAPH, citations=956)
  3. Plenoxels (2022, CVPR, citations=892)
  4. TensoRF (2022, ECCV, citations=634)
  5. Mip-NeRF 360 (2022, CVPR, citations=587)
- 输出目录：data/surveys/2026-04-22_nerf_realtime/
```

---

### `/hypo-screen` — 文献筛选分类

按自定义规则对调研结果进行筛选、分类、分析。将大候选池收敛为结构化的分类报告。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `path` | ✅ | 调研结果目录 | `"data/surveys/2026-04-22_fhe_hw/"` |
| `rules` | ✅ | 分类规则（自然语言） | 见下方示例 |
| `recall_checklist` |  | 已知重要论文列表 | `"Cinnamon, Hydra, ARK, ..."` |

**示例：**

```text
/hypo-screen path="data/surveys/2026-04-22_fhe_hw/" rules="""
A: FHE + 大模型推理 + 硬件加速器（ASIC/FPGA/GPU）
B: FHE + 硬件加速器（CNN 或更小规模模型）
C: FHE + 大模型推理（纯软件优化）
D: CIM/PIM + FHE
排除: MPC/GC/OT 为主导方案
""" recall_checklist="Cinnamon, Hydra, CraterLake, F1, ARK, TensorFHE"
```

Agent 会逐篇标注类别，输出：

```text
📋 筛选完成（1437 篇 -> 5 类）

- A（FHE + 大模型 + 硬件）= 2: Cinnamon (ASPLOS'25), Hydra (HPCA'25)
- B（FHE + 硬件）= 26: CraterLake, F1, ARK, TensorFHE, ...
- C（FHE + 大模型软件）= 17: EncryptedLLM, Iron, ...
- D（CIM/PIM + FHE）= 9
- 排除 = 7
- Recall: 24/24
- 输出：classified_papers.json, analysis_report.md
```

---

### `/hypo-search` — 快速文献检索

单次快速检索，不做 query 扩展。适合已知关键词的精确查找，或对调研结果的补充检索。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `query` | ✅ | 检索词 | `"3D Gaussian Splatting"` |
| `source` |  | 数据源 | `all`（默认） |

**示例：**

```text
/hypo-search query="CKKS bootstrapping FPGA accelerator"
```

---

### `/hypo-cite` — 引文图扩展

从种子论文出发，通过引用 / 被引关系发现相关论文。输出格式与 `/hypo-survey` 兼容，可直接传给 `/hypo-screen`。

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `seeds` | ✅ | 种子论文（DOI / arXiv ID / 标题） | `"Cinnamon, CraterLake, F1"` |
| `depth` |  | 遍历深度 | `1`（默认）/ `2` |
| `direction` |  | 方向 | `both`（默认）/ `citations` / `references` |
| `year_range` |  | 年份过滤 | `2020-2026` |

**示例：**

```text
/hypo-cite seeds="Cinnamon, CraterLake, F1" depth=1 direction=both year_range=2020-2026
```

---

### 推荐工作流

```text
# Step 1：综合调研，建立候选池
/hypo-survey topic="FHE hardware accelerator" year_range=2020-2026

# Step 2：从核心论文扩展引用图
/hypo-cite seeds="Cinnamon, CraterLake, F1, ARK" depth=1

# Step 3：按自定义规则筛选分类
/hypo-screen path="data/surveys/2026-04-22_fhe_hw/" rules="""
A: FHE + 大模型 + 硬件加速
B: FHE + 硬件（CNN 级别）
C: FHE + 大模型（软件）
D: CIM/PIM + FHE
排除: MPC/GC/OT
"""

# Step 4：根据分类报告，补充检索薄弱方向
/hypo-search query="NTT hardware architecture survey"
/hypo-search query="TFHE gate bootstrapping accelerator"

# Step 5：合并补充结果，重新筛选
/hypo-screen path="data/surveys/2026-04-22_fhe_hw/" rules="..."
```

---

## 🤝 兼容性

| Agent | 调用方式 | 安装 |
|-------|---------|------|
| **Claude Code** | `/hypo-survey` 或 `$hypo-survey` | `./install-skills.sh` |
| **Codex CLI** | `/hypo-survey` 或 `/prompts:hypo-survey` | `./install-skills.sh` |

Skills 遵循 [Agent Skills 开放标准](https://github.com/agentskills/agentskills)（SKILL.md + YAML frontmatter）。

## ⚙️ 配置说明

### Semantic Scholar API Key

设置后可大幅提升 S2 搜索速率（从 ~1 req/s 提升到 ~10 req/s）。不设置时仍可使用，但大批量搜索可能触发 rate limit。

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key-here"

# 申请: https://www.semanticscholar.org/product/api#api-key-form
```

### uv

本项目使用 [uv](https://github.com/astral-sh/uv) 管理依赖。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 🛠️ 开发

```bash
uv run pytest -v
uv run hypo-research --help
```

## 📄 License

MIT
