# Hypo-Research Developer Guide

## Repository Layout

```text
src/hypo_research/
  cli.py                  # Click CLI entrypoint
  guide/                  # deterministic natural-language router
  read/                   # PDF ingest, outline, evidence cards
  paper_target.py         # file/folder/archive target resolver
  writing/                # LaTeX stats, lint, fix, check, verify
  review/                 # paper parsing, reviewer personas, reports
  survey/ and core/       # literature search and source adapters
  project/ and meeting/   # persistent project and meeting workflows
skills/                   # source skill documents
.agents/skills/           # Codex bundle mirror
plugins/hypo-research/    # Claude plugin mirror
```

## Development Commands

```bash
uv sync
uv run pytest
uv run hypo-research --help
```

Focused checks used for paper target and guide work:

```bash
uv run pytest tests/test_paper_target.py tests/test_read.py tests/test_guide.py tests/test_check_cli.py tests/test_review_cli.py
```

## Skill Sync

Source skill docs live under `skills/`. Mirrors should be refreshed mechanically:

```bash
cp -R skills/* .agents/skills/hypo-research/skills/
cp -R skills/* plugins/hypo-research/skills/
cp .agents/skills/hypo-research/SKILL.md plugins/hypo-research/SKILL.md
```

Do not edit generated mirrors by hand when the source skill file needs the same change.

## Release Checklist

1. Ensure Cycle/Patch state is complete.
2. Run docs freshness checks.
3. Sync skill/plugin mirrors and lightweight workflow derived files.
4. Run `uv run pytest`.
5. Bump `pyproject.toml`, `uv.lock`, `.claude-plugin/marketplace.json`, and `plugins/hypo-research/.claude-plugin/plugin.json`.
6. Update `CHANGELOG.md`.
7. Commit, tag, and push when the worktree contains only intended release files.

## Paper Target Resolver

`hypo_research.paper_target.resolve_paper_target()` resolves:

- `.tex` and `.pdf` files
- directories containing one LaTeX main file or one PDF
- `.zip` and `.tar*` archives, extracted to temporary directories

Archive extraction validates member paths to reject traversal outside the temporary directory.
