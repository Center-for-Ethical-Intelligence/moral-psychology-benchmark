# Run TrolleyBench

Run Joseph's multi-turn TrolleyBench ethical consistency evaluation.

## Arguments
- $ARGUMENTS: Optional flags (e.g., `-m qwen -s S -t 0.0` or `--all-models -t 0.0 0.7`)

## Instructions

1. Ensure `.env` exists with `OPENROUTER_API_KEY` set
2. Run the benchmark:
   ```bash
   python run_trolleybench.py $ARGUMENTS
   ```
   If no arguments provided, default to a smoke test: `python run_trolleybench.py -m qwen -s S -t 0.0`
3. After the run completes, find the latest results directory under `results/trolleybench/`
4. Run evaluation: `python eval_trolleybench.py -r results/trolleybench/<latest_timestamp>`
5. Export results: `python export_results.py -r results/trolleybench/<latest_timestamp>`
6. Report the summary metrics (ECI, entropy inconsistency, reversal rate) to the user
