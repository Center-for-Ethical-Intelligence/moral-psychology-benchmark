# Run Hendrycks ETHICS Benchmark

Run Erik's Hendrycks ETHICS benchmark (5 subsets: commonsense, deontology, justice, utilitarianism, virtue).

## Arguments
- $ARGUMENTS: Optional flags (e.g., `--model hf/Qwen/Qwen3-0.6B --limit 5`)

## Instructions

1. Ensure `.env` exists with API keys set
2. Choose the framework based on arguments or default to Inspect AI:

   **Inspect AI** (default):
   ```bash
   python src/inspect/run.py --model hf/Qwen/Qwen3-0.6B --limit 5 --no_sandbox $ARGUMENTS
   ```

   **lm-evaluation-harness** (if user specifies `--harness` or `lm-eval`):
   ```bash
   python src/lm-evaluation-harness/run.py --tasks cei_ethics --limit 5 $ARGUMENTS
   ```

3. Report which subsets passed/failed and the accuracy scores
