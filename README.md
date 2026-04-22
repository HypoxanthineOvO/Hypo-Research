# Hypo-Research

Hypo-Research is an academic research assistant skill pack. This MVP focuses on
targeted literature search against the Semantic Scholar Graph API and stores
structured search output under `data/surveys/`.

## Install

```bash
python -m pip install -e ".[dev]"
```

## CLI

```bash
hypo-research search "cryogenic computing GPU" --year-start 2020 --year-end 2026 --max-results 50
```

Outputs are written to `data/surveys/{date}_{slug}/` by default:

- `meta.json`
- `results.json`
- `raw/semantic_scholar.json`
