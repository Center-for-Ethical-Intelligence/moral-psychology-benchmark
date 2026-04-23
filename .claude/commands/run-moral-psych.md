# Run Moral-Psych Benchmarks

Run Jenny's 5 moral-psychology benchmarks: UniMoral, SMID, Value Kaleidoscope, CCD-Bench, Denevil.

## Arguments
- $ARGUMENTS: Optional flags (e.g., `--tasks evals/unimoral.py --model openrouter/qwen/qwen3-8b --limit 10`)

## Instructions

1. Ensure `.env` exists with required keys and data paths:
   - `OPENROUTER_API_KEY`
   - `UNIMORAL_DATA_DIR`, `SMID_DATA_DIR`, `VALUEPRISM_RELEVANCE_FILE`, `VALUEPRISM_VALENCE_FILE`, `CCD_BENCH_DATA_FILE`, `DENEVIL_DATA_FILE`
2. Check which data paths are configured. Warn the user about any missing ones.
3. Run the benchmark:

   **All 5 benchmarks** (default if no `--tasks` specified):
   ```bash
   python src/inspect/run.py --tasks evals/moral_psych.py --model openrouter/qwen/qwen3-8b --no_sandbox $ARGUMENTS
   ```

   **Single benchmark** (if user specifies one):
   ```bash
   python src/inspect/run.py --tasks evals/<benchmark>.py --no_sandbox $ARGUMENTS
   ```

   Available benchmarks: `unimoral`, `smid`, `value_kaleidoscope`, `ccd_bench`, `denevil`

4. For SMID (vision benchmark), use a vision-capable model like `openrouter/qwen/qwen3-vl-8b-instruct`
5. Report the results summary to the user
