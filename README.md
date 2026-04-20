# CEI — Moral Psychology Benchmark Evaluation

Systematic evaluation of LLM moral reasoning across 13 Tier-1 papers from the [Center for Ethical Intelligence](https://www.ethical-intel.org/).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up your API key
cp .env.example .env
# Edit .env with your OpenRouter API key

# List available models
python run_benchmark.py --list-models

# Run a benchmark
python run_benchmark.py -b morebench --all-models -t 0.0 0.7

# Run specific models/sizes
python run_benchmark.py -b trolleybench -m qwen llama -s L M -t 0.0
```

## Project Structure

```
cei/
├── config.py                        # Models, benchmarks, temperatures
├── client.py                        # OpenRouter API client
├── run_benchmark.py                 # Batch evaluation runner
├── prompts/                         # Benchmark prompt files (JSONL)
├── results/                         # Output (gitignored)
├── meeting-notes/                   # Team meeting notes
├── moral-psychology-benchmarks.md   # 13 Tier-1 paper summaries
└── openrouter-setup.md              # OpenRouter setup guide
```

## Models

5 open-source families × 3 sizes (L, M, S):

| Family | L | M | S |
|--------|---|---|---|
| Qwen | 72B | 32B | 7B |
| DeepSeek | R1 | V3 | R1-distill-8B |
| Llama | 3.3-70B | 3.1-8B | 3.2-3B |
| Gemma | 3-27B | 3-12B | 3-4B |
| Minimax | M1-80k | M1-40k | M1-20k |

## Adding a Benchmark

1. Prepare prompts as JSONL in `prompts/<benchmark_id>.jsonl`
2. Run: `python run_benchmark.py -b <benchmark_id> --all-models`
3. Results saved to `results/<benchmark_id>/<timestamp>/`

## Team

| Person | Papers |
|--------|--------|
| Joseph | #1-5 (MoReBench, TrolleyBench, Moral Circuits, M³oralBench, MoralLens) |
| Jenny | #6-10 (UniMoral, SMID, Denevil, Value Kaleidoscope, CCD-Bench) |
| Erik | #11-13 (Rules Broken, MoralBench, EMNLP Educator) |
