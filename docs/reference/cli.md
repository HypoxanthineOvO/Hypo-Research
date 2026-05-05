# CLI Reference

Run:

```bash
uv run hypo-research --help
```

Available top-level commands:

| Command | Purpose |
|---|---|
| `guide` | Route natural-language research requests and optionally execute safe paths. |
| `read` | Ingest PDFs, render outlines, and extract evidence cards. |
| `check` | Run the writing-quality pipeline; use `--full` for submission checks. |
| `review` | Parse a paper and generate multi-reviewer simulated review scaffolds. |
| `search` | Run targeted multi-source literature search. |
| `cite` | Expand candidate papers through citation graph traversal. |
| `lint` | Inspect and optionally fix LaTeX structure issues. |
| `verify` | Verify BibTeX metadata against external sources. |
| `presubmit` | Compatibility/legacy PASS/WARNING/FAIL pre-submit wrapper. |
| `idea` | Generate research ideas. |
| `challenge` | Stress-test an idea with Socratic questions. |
| `experiment` | Design experiments for an idea. |
| `plan` | Generate a research roadmap. |
| `pilot` | Run the full ideation-to-plan flow. |
| `project` | Manage persistent research project context. |
| `rebuttal` | Parse review comments and draft rebuttal responses. |
| `meeting` | Generate structured academic meeting minutes. |
| `glossary` | Manage meeting terminology corrections. |
| `init` | Create `.hypo-research.toml`. |

## Paper Target Commands

```bash
uv run hypo-research check ./paper-folder --full
uv run hypo-research check submission.zip --full
uv run hypo-research review ./paper-folder --venue icml --panel full
uv run hypo-research read ingest paper.zip --out data/reads/paper
```
