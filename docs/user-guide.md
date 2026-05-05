# Hypo-Research User Guide

Hypo-Research is an academic research assistant toolkit for literature search, paper reading, LaTeX writing checks, simulated peer review, rebuttal drafting, ideation, planning, meetings, and project tracking.

## Install

```bash
git clone https://github.com/HypoxanthineOvO/Hypo-Research.git
cd Hypo-Research
uv sync
uv run hypo-research --help
```

Install local skills for Codex and Claude Code:

```bash
./install-skills.sh
```

## Start Here

Use `guide` when you do not know which workflow applies:

```bash
uv run hypo-research guide "我论文快投了，帮我检查一下"
uv run hypo-research guide "读一下这篇 PDF 的方法" --execute --target paper.pdf --out data/reads/paper
```

Direct commands stay first-class:

```bash
uv run hypo-research check paper.tex --full
uv run hypo-research review paper.tex --venue icml --panel full
uv run hypo-research read ingest paper.pdf --out data/reads/paper
uv run hypo-research search "LLM-assisted literature review" --max-results 20
```

## Paper Target Inputs

Paper commands accept practical submission shapes:

- `check` and `review`: `.tex`, LaTeX project folders, `.pdf`, `.zip`, `.tar`, `.tar.gz`, `.tar.bz2`, `.tar.xz`.
- `read ingest`: `.pdf`, folders with a single PDF, and the same archive formats.
- Ambiguous folders or archives stop with a candidate list.

## Common Workflows

### Submission Check

```bash
uv run hypo-research check ./paper-folder --full
uv run hypo-research check submission.zip --full
```

Use `--no-fix` for report-only mode and `--json` for machine-readable output.

### PDF Reading

```bash
uv run hypo-research read ingest paper.pdf --out data/reads/paper
uv run hypo-research read outline data/reads/paper/artifact.json
uv run hypo-research read extract data/reads/paper/artifact.json --out data/reads/paper/cards
```

`read extract` produces method, dataset, figure/table, and claim evidence cards.

### Simulated Review

```bash
uv run hypo-research review paper.tex --venue icml --panel full --severity standard
uv run hypo-research review paper.pdf --venue neurips --no-literature
```

Use `--list-reviewers` and `--list-venues` to inspect built-in review settings.

### Literature Search

```bash
uv run hypo-research search "transformer architecture" --max-results 20
uv run hypo-research search "LLM for code generation" -eq "program synthesis benchmark"
```

Search writes JSON, BibTeX, and Markdown reports unless disabled with options.

## Skills

The 21 skills are grouped as:

- First-line: `hypo-guide`, `hypo-check`, `hypo-review`, `hypo-read`
- Literature: `hypo-survey`, `hypo-search`, `hypo-screen`, `hypo-cite`
- Writing: `hypo-lint`, `hypo-verify`, `hypo-presubmit`, `hypo-polish`, `hypo-translate`
- Ideation: `hypo-idea`, `hypo-challenge`, `hypo-experiment`, `hypo-plan`, `hypo-pilot`
- Project and communication: `hypo-project`, `hypo-meeting`, `hypo-rebuttal`

## More References

- CLI reference: `docs/reference/cli.md`
- Developer guide: `docs/developer.md`
- Platform notes: `docs/platforms/codex-claude.md`
