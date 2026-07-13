# AGENTS.md

This file gives coding agents a fast, reliable operating guide for this repository.

## Project Snapshot

- Project: `ml-project`
- Language: Python `>=3.12`
- Package manager / runner: `uv`
- Main domain: NYC taxi ride demand prediction and time-series feature engineering
- Primary workflow: explore in notebooks, promote reusable logic into `src/`

## Repo Map

- `src/`: reusable Python package code
- `src/pipelines/features/`: data download, raw-data validation, time-series conversion, and feature/target generation
- `src/utils/paths.py`: project-relative paths for local data, cache, and model directories
- `notebooks/`: exploratory notebooks that mirror and validate the pipeline steps
- `data/`: local raw, transformed, and cached datasets; do not commit generated data
- `models/`: local trained model artifacts if created; do not commit generated models
- `main.py`: minimal project entrypoint
- `.env.sample`: template for local service credentials

## Local Setup

```bash
uv sync
```

Run the sample entrypoint:

```bash
uv run python main.py
```

Start notebooks:

```bash
uv run jupyter notebook
```

## Common Commands

Run a Python module or script:

```bash
uv run python path/to/script.py
```

Compile-check the package when no test suite is available:

```bash
uv run python -m compileall src main.py
```

If tests are added later, run them with:

```bash
uv run pytest
```

## Data Workflow Notes

- Raw taxi parquet files are downloaded from the NYC TLC public trip-data bucket.
- `src.utils.paths` creates local `data/`, `data/raw/`, `data/transformed/`, `data/cache/`, and `models/` directories on import.
- Keep local data and model artifacts out of git.
- Prefer deterministic transformations in `src/`; use notebooks for exploration, inspection, and plots.
- When moving notebook logic into `src/`, preserve column contracts:
  - raw validated rides: `pickup_datetime`, `pickup_location_id`
  - time-series data: `pickup_hour`, `pickup_location_id`, `rides`
  - supervised features: previous ride counts plus `pickup_hour` and `pickup_location_id`

## Quality Gates

There is no configured lint or test suite in the current project. Before handoff, run the strongest relevant checks available:

```bash
uv run python -m compileall src main.py
```

For behavior changes, add focused tests when practical and run them. If a check cannot be run because tooling is absent, say that explicitly in the handoff.

## Change Expectations for Agents

- Keep changes minimal and scoped to the request.
- Do not refactor unrelated notebook or pipeline code in the same change.
- Preserve existing data contracts unless the task explicitly asks for a contract change.
- Update notebooks only when the request is notebook-specific or the notebook would otherwise become misleading.
- Update this file when the user corrects agent behavior and the correction should guide future work.

## Python Standards

- Follow PEP 8 and the style already present in nearby files.
- Use type hints on new public function signatures.
- Prefer explicit pandas transformations over clever chained expressions when readability would suffer.
- Avoid broad `except` blocks in new code; catch specific exceptions when possible.
- Do not hardcode secrets, credentials, personal absolute paths, or machine-specific configuration.
- Put reusable paths in `src/utils/paths.py` or pass paths as parameters.

## Safety Notes

- Do not commit `.env`, API keys, service credentials, raw data, transformed data, cache files, or model artifacts.
- Be careful with commands that download large public datasets; check whether the target file already exists.
- Avoid destructive file operations in `data/` and `models/` unless the user explicitly asks for cleanup.
- Network-dependent steps, such as downloading NYC TLC parquet files, may fail or be slow; handle failures clearly.

## Agent Operating Rules

### 1. Explore First

- Use the available codebase-retrieval MCP tool before editing when file locations or project patterns are not obvious.
- Read the nearest relevant files before changing code.
- Prefer the current project's root directory as the search context.

### 2. Describe the Approach

- Briefly state the intended approach before making non-trivial edits.
- Ask clarifying questions when requirements are ambiguous or multiple interpretations would produce different behavior.
- For simple, clearly scoped tasks, proceed after the short approach.

### 3. Limit Scope

- Change only what the request requires.
- Do not reformat, rename, or reorganize unrelated code.
- If a task would touch more than three files, explain the breakdown before editing.

### 4. Bug Fix Protocol

- Reproduce the bug with a failing test or minimal local check when practical.
- Fix the root cause rather than only patching the visible symptom.
- Re-run the relevant check after the fix.

### 5. Post-Change Review

- Summarize what changed.
- List checks run and their results.
- Note any meaningful risks, especially data-contract, notebook, or dependency impacts.

## Quality Priority Order

```text
Correctness > Simplicity > Maintainability > Performance
```

If the solution is hard to explain, hard to debug, or hard to reproduce, it is probably wrong.
