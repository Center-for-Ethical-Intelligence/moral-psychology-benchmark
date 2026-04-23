---
name: cei-benchmark-patterns
description: Coding patterns for the CEI moral psychology benchmark evaluation platform
version: 1.0.0
source: local-git-analysis
analyzed_commits: 20
---

# CEI Benchmark Patterns

## Commit Conventions

This project uses **conventional commits** (100% adoption):

| Prefix | Usage | Share |
|--------|-------|-------|
| `docs:` | Documentation, README updates, meeting notes | 50% |
| `feat:` | New benchmarks, pipelines, integrations | 30% |
| `fix:` | Bug fixes, model ID corrections | 10% |
| `chore:` | Cleanup, gitignore, maintenance | 10% |

Examples:
```
feat: merge Jenny's moral-psych benchmark suite (5 benchmarks)
feat: implement TrolleyBench multi-turn evaluation pipeline
fix: correct action extraction, variant mapping, and API key validation
docs: add architecture diagrams to README
chore: remove obsolete result runs (smoke test + bad model IDs)
```

## Code Architecture

```
cei/
├── *.py                            # Top-level pipeline scripts (Joseph's TrolleyBench)
│   ├── config.py                   # Model registry, temperatures, paper assignments
│   ├── client.py                   # OpenRouter API client (query, multiturn)
│   ├── run_trolleybench.py         # Multi-turn runner
│   ├── eval_trolleybench.py        # ECI + entropy evaluation
│   └── export_results.py           # CSV/markdown exporter
├── src/inspect/                    # Inspect AI framework
│   ├── run.py                      # Enhanced CLI runner (shared across all Inspect benchmarks)
│   ├── pyproject.toml              # Package dependencies (inspect_ai, openai)
│   └── evals/                      # Task definitions (one file per benchmark)
│       ├── ethics.py               # Erik's Hendrycks ETHICS (5 tasks)
│       ├── _benchmark_utils.py     # Shared utilities (Jenny)
│       ├── moral_psych.py          # Task registry importing all benchmarks
│       ├── unimoral.py             # UniMoral (4 tasks)
│       ├── smid.py                 # SMID vision (2 tasks)
│       ├── value_kaleidoscope.py   # Value Kaleidoscope (2 tasks)
│       ├── ccd_bench.py            # CCD-Bench (1 task)
│       ├── denevil.py              # Denevil (2 tasks)
│       └── data/                   # Prompt templates
├── src/lm-evaluation-harness/      # lm-eval framework (Erik)
│   ├── run.py                      # CLI wrapper
│   └── tasks/                      # YAML task configs
├── scripts/                        # Batch runners, release builders (Jenny)
├── tests/                          # test_<module>.py naming convention
├── results/                        # Timestamped outputs per benchmark
│   ├── trolleybench/<timestamp>/   # TrolleyBench JSON results
│   ├── inspect/logs/               # Inspect AI eval logs
│   ├── release/<date>-<tag>/       # Frozen release packages
│   └── lm-harness/                 # lm-eval results
├── docs/                           # User guides, reproducibility, history
├── figures/release/                # SVG charts
├── vendor/                         # Vendored Python wheels
└── .claude/commands/               # Claude Code slash commands
```

## Workflows

### Adding a New Inspect AI Benchmark

1. Create task file in `src/inspect/evals/<benchmark_name>.py`
   - Use `@task` decorator for each task variant
   - Import shared utilities from `_benchmark_utils.py`
   - Data loading from env vars (e.g., `os.environ["BENCHMARK_DATA_DIR"]`)
2. Register tasks in `src/inspect/evals/moral_psych.py` TASK_EXPORTS list
3. Add data path env vars to `.env.example`
4. Add tests in `tests/test_<benchmark_name>.py`
5. Update README.md with benchmark documentation

### Adding a New TrolleyBench-Style Pipeline

1. Create prompts as JSONL in `prompts/<benchmark_id>.jsonl`
2. Write runner script: `run_<benchmark>.py` (use `client.py` for API calls)
3. Write evaluator: `eval_<benchmark>.py`
4. Write exporter: `export_results.py` (or extend existing)
5. Results saved to `results/<benchmark_id>/<timestamp>/`

### Running Benchmarks

All benchmarks use OpenRouter as the API gateway. Setup:
```bash
cp .env.example .env   # add OPENROUTER_API_KEY
pip install -r requirements.txt
```

Run patterns:
```bash
# TrolleyBench (custom pipeline)
python run_trolleybench.py -m <family> -s <size> -t <temp>

# Inspect AI benchmarks (shared runner)
python src/inspect/run.py --tasks evals/<benchmark>.py --model <model> --no_sandbox

# lm-evaluation-harness
python src/lm-evaluation-harness/run.py --tasks <task_group> --limit <n>
```

### Contributing Code

1. Create branch: `git checkout -b <type>/<description>`
2. Make changes and commit with conventional commit format
3. Push and create PR against `main`
4. Add a teammate as reviewer (direct push to `main` is blocked)
5. Or use Claude Code: `/create-pr`

### Building Release Artifacts

```bash
make release           # Rebuilds CSVs, SVGs, reports
make test              # Runs all 9 test files
make audit             # Verifies release integrity
```

## Testing Patterns

- **Location:** `tests/` directory (flat, no subdirectories)
- **Naming:** `test_<module_name>.py` (e.g., `test_inspect_run.py`, `test_moral_psych_tasks.py`)
- **Framework:** pytest
- **Categories:**
  - Task builder tests (`test_moral_psych_tasks.py`)
  - Runner/CLI tests (`test_inspect_run.py`)
  - Framework integration tests (`test_lm_harness_*.py`, `test_inspect_ethics.py`)
  - Release/artifact tests (`test_release_artifacts.py`)
  - Repo hygiene tests (`test_repo_hygiene.py`)
- **Run:** `python -m pytest tests/ -q` or `make test`

## Model Naming Convention

Models are organized by family and size slot:

| Slot | Meaning |
|------|---------|
| `S` (Small) | Smallest model in family |
| `M` (Medium) | Mid-range model |
| `L` (Large) | Largest model in family |

Model IDs use OpenRouter format: `openrouter/<provider>/<model-name>`

5 families: Qwen, DeepSeek, Llama, Gemma, MiniMax

## Environment Variables

All secrets and data paths go in `.env` (never committed):
- `OPENROUTER_API_KEY` — required for all benchmarks
- `HF_TOKEN` — for HuggingFace datasets
- `*_DATA_DIR` / `*_DATA_FILE` — per-benchmark data paths

## Key Conventions

- **Immutable results:** Results are timestamped and never overwritten
- **Frozen releases:** Release snapshots are tagged by date (e.g., `2026-04-19-option1`)
- **One file per benchmark:** Each benchmark gets its own `.py` in `evals/`
- **Shared runner:** All Inspect AI benchmarks share `src/inspect/run.py`
- **Branch protection:** All changes via PR, no direct pushes to `main`
