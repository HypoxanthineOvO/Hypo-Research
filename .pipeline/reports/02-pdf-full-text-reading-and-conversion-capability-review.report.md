# M03 报告：PDF / 全文阅读 / 文档转换能力调研

## 结论

Hypo-Research 应新增一条 `读论文` 能力线，核心不是“PDF 转文本”，而是 **把论文转成可追问的结构化证据对象**。短期推荐采用三层策略：

1. 基线层：`pdftotext` / `pdfimages` / PyMuPDF，低依赖、可快速抽取文本、页码、图片。
2. 结构层：GROBID 或 Docling，将论文恢复为 TEI/Markdown/HTML/JSON 等结构化表示。
3. 语义层：Agent 对 methods、datasets、figures、claims 做问题驱动抽取和证据矩阵。

默认安装当前没有 `fitz/PyMuPDF`、Docling、Marker 等依赖；现有 `review.parser` 的 PDF 路径依赖 `fitz`，所以默认 `uv sync` 后不能可靠解析 PDF。系统命令 `pdftotext`、`pdfimages`、`mutool` 可用，适合作为无新增依赖的 fallback。

## 外部工具调研

| 工具 | 适合做什么 | 优点 | 风险 |
|---|---|---|---|
| GROBID | 学术 PDF 到 TEI XML | 专注 scientific publication，结构化文档、参考文献、章节 | 输出是 TEI，需要二次转 Markdown/JSON；图表内容理解弱 |
| Docling | 多格式文档到 Markdown/HTML/JSON | 支持 PDF layout、reading order、table structure、formula、image、OCR、本地执行和 AI 集成 | 依赖较重，科研论文场景需要实测 |
| Nougat | 学术文档 OCR 到 markup | 对数学/学术文档机器可读化有研究基础 | 模型型 OCR，资源成本和表格鲁棒性需验证 |
| Marker | PDF 到 Markdown | 面向快速 Markdown 输出和图片/metadata | 生态和维护状态需再确认 |
| PyMuPDF / PyMuPDF4LLM | 本地文本/块/图片抽取 | 轻量、易集成、适合作为 fallback | 结构恢复有限，表格/公式/阅读顺序不稳定 |
| pdftotext/pdfimages | 系统级 fallback | 已可用、无需 Python 依赖 | 只能得到粗文本和图片列表，语义结构弱 |

参考来源：

- GROBID 文档说明其目标是将 PDF 等 raw documents 转成结构化 XML/TEI，面向 scientific publications：https://grobid.readthedocs.io/en/latest/Principles/
- Docling 官方文档列出 PDF layout、reading order、table structure、formula、OCR、Markdown/HTML/JSON 导出等能力：https://docling-project.github.io/docling/
- Docling 产品页强调 table、formula、reading order、picture extraction、caption、bounding boxes：https://www.docling.ai/
- Nougat 论文提出将科学文档 OCR 成 markup language：https://arxiv.org/abs/2308.13418

## 本地原型观察

使用仓库内两篇 PDF：

- `data/reviews/FRR/FRRPaper.pdf`
- `data/reviews/NeuRex/NeuRex.pdf`

命令：

```bash
pdftotext -layout data/reviews/FRR/FRRPaper.pdf .pipeline/reports/pdf-prototype/frr/text.txt
pdfimages -list data/reviews/FRR/FRRPaper.pdf > .pipeline/reports/pdf-prototype/frr/images.txt
pdftotext -layout data/reviews/NeuRex/NeuRex.pdf .pipeline/reports/pdf-prototype/neurex/text.txt
pdfimages -list data/reviews/NeuRex/NeuRex.pdf > .pipeline/reports/pdf-prototype/neurex/images.txt
```

结果：

- FRR 文本抽取 906 行，NeuRex 文本抽取 1229 行。
- FRR 可列出图像对象，示例中第 7、10、11、12、13 页存在多张 image/smask，说明图片资产可被粗粒度发现。
- `pdftotext -layout` 能保留部分双栏布局和 caption 文本，但会把正文、图注、公式、图中文字混排在一起。
- 图像列表能告诉我们“哪一页有图片”，但不能直接关联 `Fig. 1` 的 caption、图片语义和正文 claim。

原型产物：

- `.pipeline/reports/pdf-prototype/frr/text.txt`
- `.pipeline/reports/pdf-prototype/frr/images.txt`
- `.pipeline/reports/pdf-prototype/neurex/text.txt`
- `.pipeline/reports/pdf-prototype/neurex/images.txt`

## 分级全文阅读模型

| 层级 | 输入 | 输出 | 典型问题 |
|---|---|---|---|
| L0 元数据/摘要 | title、abstract、venue、year、citation | 是否相关、领域初判 | 这篇值得读吗？ |
| L1 Intro/Conclusion | intro、conclusion、claim sentence | motivation、contribution、限制 | 它解决什么问题？ |
| L2 方法/数据/图表 | method section、experiment section、figures/tables/captions | method card、dataset card、figure card、claim evidence | 用了什么方法？跑了什么数据？图说明什么？ |
| L3 全文结构化笔记 | 全文章节和引用 | structured notes、open questions | 这篇论文整体怎么讲？ |
| L4 多篇证据矩阵 | 多篇 L2/L3 输出 | method/dataset/claim matrix | 这些论文谁证明了什么？差异在哪里？ |

## 推荐接口草案

```text
hypo-research read ingest paper.pdf --out data/read/<slug>
hypo-research read outline data/read/<slug>
hypo-research read ask data/read/<slug> "用了什么方法？"
hypo-research read extract data/read/<slug> --focus methods,datasets,figures,claims
hypo-research read compare data/read/a data/read/b --matrix claims
```

内部对象：

```yaml
PaperReadArtifact:
  source_pdf: path
  text_layers:
    raw_text: text
    sections: []
    captions: []
  assets:
    figures: []
    tables: []
  evidence_cards:
    methods: []
    datasets: []
    figures: []
    claims: []
  quality:
    extraction_confidence: low|medium|high
    missing_sections: []
```

## 推荐 pipeline

1. Ingest：PDF hash、page count、metadata。
2. Extract：先跑 fallback `pdftotext/pdfimages`，如果安装了 Docling/GROBID/PyMuPDF，则跑结构化抽取。
3. Normalize：统一为 `PaperReadArtifact`。
4. Segment：章节、caption、references、claim sentence。
5. Evidence extraction：method、dataset、figure、claim support。
6. Ask/Report：按问题选择 L0-L4 读取深度。

## 风险

- 表格和公式是最大风险：纯文本抽取不足，Docling/GROBID/Nougat 也需按领域实测。
- 图片语义必须依赖 caption、正文引用和可选 VLM，不应只靠图像像素。
- Claim 支撑判断容易越界成审稿，需要报告“不确定”和证据缺口。
- 用户私有 PDF 可能涉及版权和隐私，默认应优先本地解析。

## 下一步

1. 新增 `review` optional dependency 或 `read` extra：`pymupdf`、可选 `docling`。
2. 先实现 fallback extractor，确保没有重依赖也能生成粗结构。
3. 设计 `PaperReadArtifact` schema 和 evidence card。
4. 用用户提供的 2 篇 PDF 再做一次真实验证，重点看 figure/caption/claim linking。
