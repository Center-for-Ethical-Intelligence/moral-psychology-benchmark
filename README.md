# CEI — Moral Psychology Benchmark Evaluation

Systematic evaluation of LLM moral reasoning across 13 Tier-1 papers from the [Center for Ethical Intelligence](https://www.ethical-intel.org/).

## Architecture

```
                                    CEI Benchmark Pipeline
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 ��                                                                                 │
 │  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐ │
 │  │   Scenario    │     │   Runner     │     │  Evaluator   │     │  Exporter  │ │
 │  │   Prompts     │────▶│              │────▶│              │────▶│            │ │
 │  │              │     │              │     │              │     │            │ │
 │  │ trolleybench │     │ run_trolley  │     │ eval_trolley │     │ export_    │ │
 │  │   .jsonl     │     │  bench.py    │     │  bench.py    │     │ results.py │ │
 │  └──────────────┘     └──────┬───────┘     └──────────────┘     └────────────┘ │
 │                              │                                                  │
 │  ┌──────────────┐     ┌──────┴───────┐                                         │
 │  │   Config     │     │   Client     │                                         │
 │  │              │────▶│              │                                         │
 │  │ config.py    │     │ client.py    │                                         │
 │  │ • 15 models  │     │ • query()    │                                         │
 │  │ • 4 temps    │     │ • multiturn()│                                         │
 │  │ • 13 papers  │     │ • w/ system()│                                         │
 │  └──────────────┘     └──────┬───────┘                                         │
 │                              │                                                  │
 └──────────────────────────────┼──────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    OpenRouter API      │
                    │  openrouter.ai/api/v1  │
                    ├───────────────────────┤
                    │ Qwen3    (235B/32B/8B)│
                    │ DeepSeek (R1/V3/70B)  │
                    │ Llama    (70B/8B/3B)  │
                    │ Gemma    (27B/12B/4B) │
                    │ MiniMax  (M2.5/M1/01) │
                    └───────────────────────┘
```

### Data Flow (TrolleyBench)

```
prompts/trolleybench.jsonl          18 scenarios × 3 turns each
         │
         ▼
run_trolleybench.py                 For each model × temperature:
         │                            T1: Present dilemma ──▶ R1
         │                            T2: Clarifying followup (with R1 context) ──▶ R2
         │                            T3: Contradictory challenge (with R1+R2) ──▶ R3
         ▼
results/<timestamp>/
  ├── qwen-L_T0.0.json             Raw multi-turn conversations
  ├── qwen-L_T0.7.json
  ├── ...
  └── meta.json
         │
         ▼
eval_trolleybench.py                Extract actions + frameworks via regex
         │                          ┌─────────────────────────────────────┐
         │                          │  Response ──▶ extract_action()      │
         │                          │    "I would pull the lever"  → act  │
         │                          │    "I refuse to act"     → no_act   │
         │                          │                                     │
         │                          │  Response ──▶ extract_framework()   │
         │                          │    "greatest good"  → consequentialist │
         │                          │    "moral duty"     → deontological    │
         │                          └─────────────────────────────────────┘
         │
         ├──▶ ECI (Ethical Consistency Index)
         │      Compare dominant action across variant pairs
         │      1.0 = always same choice, 0.0 = always different
         │
         ├──▶ Entropy Inconsistency
         │      Binary entropy of act/no_act across 3 turns
         │      0.0 = never wavers, 1.0 = maximally unpredictable
         │
         ├──▶ Follow-up Reversal Rate
         │      % of T3 responses that flip T1 position
         │
         ▼
  ├── eval_summary.json             Per-model metrics
  └── eval_report.md                Human-readable report
         │
         ▼
export_results.py
  ├── export/summary.csv            One row per model
  ├── export/all_responses.csv      One row per scenario × model
  └── export/conversations.md       Full conversations, readable
```

### Trolley Variant Coverage

```
                        ┌─────────────────────┐
                        │   Classic Trolley    │
                        │      Problem         │
                        └──────────┬──────────┘
           ┌───────────┬───────────┼───────────┬────────────┐
           ▼           ▼           ▼           ▼            ▼
      ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
      │ Switch  │ │Footbridge│ │  Loop   │ │Trapdoor │ │Man-in-  │
      │ (lever) │ │ (push)  │ │(divert) │ │(button) │ │ front   │
      └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
       action vs    physical    intended     indirect     direct
       inaction     contact     vs foreseen  mechanism    force
           ┌───────────┬───────────┬────────────┬────────────┐
           ▼           ▼           ▼            ▼            ▼
      ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐
      │Saboteur │ │ Organ   │ │  Self-  │ │Autonomous│ │Bystander│
      │ (guilt) │ │Transplant│ │Sacrifice│ │ Vehicle  │ │ Dilemma │
      └─────────┘ └─────────┘ └─────────┘ └──────────┘ └─────────┘
       desert/      institu-    self vs      programmed   certainty
       guilt        tional      other        ethics       vs uncert.
                    trust
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env with your OpenRouter API key (and optionally HF_TOKEN, OPENAI/ANTHROPIC keys)

# --- TrolleyBench (multi-turn, OpenRouter API) ---

# Run TrolleyBench (smoke test)
python run_trolleybench.py -m qwen -s S -t 0.0

# Run full evaluation
python run_trolleybench.py --all-models -t 0.0 0.7

# Evaluate results
python eval_trolleybench.py -r results/trolleybench/<timestamp>

# Export to CSV/markdown
python export_results.py -r results/trolleybench/<timestamp>

# --- Hendrycks ETHICS (via Inspect AI) ---

python src/inspect/run.py --model hf/Qwen/Qwen3-0.6B --limit 5 --no_sandbox

# --- Hendrycks ETHICS (via lm-evaluation-harness) ---

python src/lm-evaluation-harness/run.py --tasks cei_ethics --limit 5

# --- Docker ---

docker compose run lm-harness
docker compose run inspect
```

## Hendrycks ETHICS Benchmark

The repo also includes the [Hendrycks ETHICS](https://arxiv.org/abs/2008.02275) benchmark (2020) with two evaluation frameworks, contributed by **Erik Nordby**.

### 5 ETHICS Subsets

| Subset | Task | Label Semantics |
|--------|------|----------------|
| Commonsense | Classify actions as ethical/unethical | 0=unethical, 1=ethical |
| Deontology | Judge scenario+excuse as excusable/inexcusable | 0=inexcusable, 1=excusable |
| Justice | Classify scenarios as just/unjust | 0=unjust, 1=just |
| Utilitarianism | Compare paired scenarios for utility | baseline always preferred |
| Virtue | Determine if trait is exhibited in scenario | 0=not exhibited, 1=exhibited |

### Inspect AI Framework

Uses [Inspect AI](https://inspect.ai/) (UK AISI) with `@task`-decorated functions in `src/inspect/evals/ethics.py`. Each task creates a `Task` with `MemoryDataset`, zero-shot generation (`max_tokens=16, temperature=0.01`), and pattern scoring (`r"\b([01])\b"`).

```bash
python src/inspect/run.py --model hf/Qwen/Qwen3-0.6B --limit 5 --no_sandbox
```

### lm-evaluation-harness Framework

Uses [lm-eval](https://github.com/EleutherAI/lm-evaluation-harness) with custom YAML task configs in `src/lm-evaluation-harness/tasks/`. Supports the `cei_ethics` task group covering all 5 subsets.

```bash
python src/lm-evaluation-harness/run.py --tasks cei_ethics --limit 5
```

## Project Structure

```
cei/
├── config.py                        # Models, benchmarks, temperatures
├── client.py                        # OpenRouter API client
├── run_benchmark.py                 # Generic single-turn runner
├── run_trolleybench.py              # Multi-turn TrolleyBench runner
├── eval_trolleybench.py             # ECI + entropy evaluation
├── export_results.py                # CSV/markdown exporter
├── prompts/                         # Benchmark prompt files (JSONL)
│   └── trolleybench.jsonl           # 18 trolley scenarios × 3 turns
├── src/
│   ├── inspect/                     # Inspect AI framework (Erik)
│   │   ├── run.py                   # CLI wrapper
│   │   ├── pyproject.toml           # Package dependencies
│   │   └── evals/
│   │       └── ethics.py            # 5 ETHICS task definitions
│   └── lm-evaluation-harness/       # lm-eval framework (Erik)
│       ├── run.py                   # CLI wrapper
│       ├── pyproject.toml           # Package dependencies
│       └── tasks/
│           ├── _cei_ethics.yaml     # Task group config
│           ├── cei_ethics_*.yaml    # 5 subset task configs
│           └── utils.py             # Utilitarianism/virtue helpers
├── vendor/                          # Vendored Python wheels
├── tests/                           # Unit tests
├── results/                         # Timestamped run outputs
│   ├── trolleybench/                # TrolleyBench results
│   ├── inspect/logs/                # Inspect AI eval logs
│   └── lm-harness/                  # lm-eval-harness results
├── Dockerfile                       # Multi-stage Docker build
├── docker-compose.yml               # Docker services
├── pyproject.toml                   # uv workspace root
├── requirements.txt                 # pip dependencies (TrolleyBench)
├── meeting-notes/                   # Team meeting notes
├── moral-psychology-benchmarks.md   # 13 Tier-1 paper summaries
└── openrouter-setup.md              # OpenRouter setup guide
```

## Models

5 open-source families × 3 sizes (L, M, S) via [OpenRouter](https://openrouter.ai):

| Family | L (Large) | M (Medium) | S (Small) |
|--------|-----------|------------|-----------|
| Qwen3 | 235B-A22B | 32B | 8B |
| DeepSeek | R1 | Chat V3.1 | R1-Distill-70B |
| Llama | 3.3-70B | 3.1-8B | 3.2-3B |
| Gemma 3 | 27B | 12B | 4B |
| MiniMax | M2.5 | M1 | 01 |

## Adding a Benchmark

1. Prepare prompts as JSONL in `prompts/<benchmark_id>.jsonl`
2. Write a runner (single-turn: use `run_benchmark.py`, multi-turn: see `run_trolleybench.py`)
3. Write an evaluator (see `eval_trolleybench.py` for reference)
4. Results saved to `results/<benchmark_id>/<timestamp>/`

## Team

| Person | Papers |
|--------|--------|
| Joseph | #1-5 (MoReBench, TrolleyBench, Moral Circuits, M3oralBench, MoralLens) |
| Jenny | #6-10 (UniMoral, SMID, Denevil, Value Kaleidoscope, CCD-Bench) |
| Erik | #11-13 (Rules Broken, MoralBench, EMNLP Educator) |
