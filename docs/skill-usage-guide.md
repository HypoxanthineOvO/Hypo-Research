# Hypo-Research Skill Usage Guide

Hypo-Research provides 21 skills plus the `hypo-research` CLI. For first-time use, start with `hypo-guide`; for known workflows, call the direct skill or CLI command.

## First-Line Skills

| Skill | CLI | Use When |
|---|---|---|
| `hypo-guide` | `guide` | You have a natural-language request and want the right workflow. |
| `hypo-check` | `check --full` | A paper is close to submission and needs writing/LaTeX/BibTeX checks. |
| `hypo-review` | `review` | You want multi-persona simulated peer review. |
| `hypo-read` | `read` | You want to ingest, outline, or deep-read a PDF. |

## Paper Targets

Paper targets can be single files, directories, or supported archives.

- `check` / `review`: `.tex`, LaTeX project directories, `.pdf`, `.zip`, and `.tar*`.
- `read ingest`: `.pdf`, directories with one PDF, `.zip`, and `.tar*`.
- Multiple candidate files are reported explicitly; pass the exact target file to disambiguate.

Examples:

```bash
uv run hypo-research check ./paper-folder --full
uv run hypo-research check submission.zip --full
uv run hypo-research review ./paper-folder --venue icml --panel full
uv run hypo-research read ingest paper.zip --out data/reads/paper
uv run hypo-research guide "我论文快投了，帮我检查一下" --execute --target submission.zip
```

## Expert Skills

| Area | Skills |
|---|---|
| Literature | `hypo-survey`, `hypo-search`, `hypo-screen`, `hypo-cite` |
| Writing | `hypo-lint`, `hypo-verify`, `hypo-check`, `hypo-presubmit`, `hypo-polish`, `hypo-translate` |
| Reading | `hypo-read` |
| Review/Rebuttal | `hypo-review`, `hypo-rebuttal` |
| Ideation/Planning | `hypo-idea`, `hypo-challenge`, `hypo-experiment`, `hypo-plan`, `hypo-pilot` |
| Project/Meeting | `hypo-project`, `hypo-meeting` |

## CLI Quick Reference

```bash
uv run hypo-research guide "读一下这篇 PDF 的方法"
uv run hypo-research search "LLM for code generation" --max-results 10
uv run hypo-research read ingest paper.pdf --out data/reads/paper
uv run hypo-research read outline data/reads/paper/artifact.json
uv run hypo-research check paper.tex --full
uv run hypo-research review paper.tex --venue icml --panel full
uv run hypo-research project status my-project
```

## Configuration

Initialize `.hypo-research.toml` in a paper or project directory:

```bash
uv run hypo-research init
uv run hypo-research init --dir ./paper
```

Priority order:

1. CLI arguments
2. `.hypo-research.toml`
3. environment variables
4. built-in defaults

Common sections:

- `[project] main_file / bib_files / src_dir`
- `[lint] disabled_rules / fix_rules`
- `[verify] timeout / skip_keys / max_concurrent`
- `[survey] default_topic / max_results / sources`

## Platform Usage

After `./install-skills.sh`, Codex CLI prompt copies and Claude Code skill links are refreshed from `skills/`.

Codex can also install the bundle from GitHub:

```text
$skill-installer https://github.com/HypoxanthineOvO/Hypo-Research/tree/main/.agents/skills/hypo-research
```

For full usage, see `docs/user-guide.md` and `docs/reference/cli.md`.
