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
# Edit .env with your OpenRouter API key

# Run TrolleyBench (smoke test)
python run_trolleybench.py -m qwen -s S -t 0.0

# Run full evaluation
python run_trolleybench.py --all-models -t 0.0 0.7

# Evaluate results
python eval_trolleybench.py -r results/trolleybench/<timestamp>

# Export to CSV/markdown
python export_results.py -r results/trolleybench/<timestamp>
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
├── results/                         # Timestamped run outputs
│   └── trolleybench/
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
