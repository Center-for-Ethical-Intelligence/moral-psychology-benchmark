#!/usr/bin/env bash
# Run all 4 Joseph benchmarks across all 15 model lines via OpenRouter.
# Usage: ./run_all_benchmarks.sh [--limit N]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load API key
export OPENAI_API_KEY="$(grep OPENROUTER_API_KEY .env | cut -d= -f2)"
export OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Data directories
export MOREBENCH_DATA_DIR="$SCRIPT_DIR/data/morebench"
export MORAL_CIRCUITS_DATA_DIR="$SCRIPT_DIR/data/moral_circuits"
export M3ORAL_DATA_DIR="$SCRIPT_DIR/data/m3oralbench"
export MORALLENS_DATA_DIR="$SCRIPT_DIR/data/morallens"

# Parse args
LIMIT_ARGS=()
if [[ "${1:-}" == "--limit" ]] && [[ -n "${2:-}" ]]; then
    LIMIT_ARGS=("--limit" "$2")
    echo ">>> Running with --limit $2"
fi

# All 15 model routes via OpenRouter
MODELS=(
    "qwen/qwen3-8b"
    "qwen/qwen3-32b"
    "qwen/qwen3-235b-a22b"
    "deepseek/deepseek-r1-distill-llama-70b"
    "deepseek/deepseek-chat-v3.1"
    "deepseek/deepseek-r1"
    "meta-llama/llama-3.2-3b-instruct"
    "meta-llama/llama-3.1-8b-instruct"
    "meta-llama/llama-3.3-70b-instruct"
    "google/gemma-3-4b-it"
    "google/gemma-3-12b-it"
    "google/gemma-3-27b-it"
    "minimax/minimax-01"
    "minimax/minimax-m1"
    "minimax/minimax-m2.5"
)

# Benchmarks to run
BENCHMARKS=(
    "evals/morebench.py"
    "evals/moral_circuits.py"
    "evals/m3oralbench.py"
    "evals/morallens.py"
)

BENCHMARK_NAMES=(
    "MoReBench"
    "MoralCircuits"
    "M3oralBench"
    "MoralLens"
)

RESULTS_LOG="$SCRIPT_DIR/results/run_log_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p "$SCRIPT_DIR/results"

echo "=== CEI Benchmark Run ===" | tee "$RESULTS_LOG"
echo "Started: $(date)" | tee -a "$RESULTS_LOG"
echo "Models: ${#MODELS[@]}" | tee -a "$RESULTS_LOG"
echo "Benchmarks: ${#BENCHMARKS[@]}" | tee -a "$RESULTS_LOG"
echo "" | tee -a "$RESULTS_LOG"

TOTAL=${#MODELS[@]}
MODEL_NUM=0

for MODEL in "${MODELS[@]}"; do
    MODEL_NUM=$((MODEL_NUM + 1))
    MODEL_SLUG=$(echo "$MODEL" | tr '/' '_')

    echo ">>> [$MODEL_NUM/$TOTAL] Model: $MODEL" | tee -a "$RESULTS_LOG"

    BENCH_IDX=0
    for BENCH in "${BENCHMARKS[@]}"; do
        BENCH_NAME="${BENCHMARK_NAMES[$BENCH_IDX]}"
        BENCH_IDX=$((BENCH_IDX + 1))

        echo "  >> $BENCH_NAME ($BENCH)" | tee -a "$RESULTS_LOG"
        echo "  >> Started: $(date)" | tee -a "$RESULTS_LOG"

        (
            cd "$SCRIPT_DIR/src/inspect"
            if uv run --package cei-inspect python run.py \
                --tasks "$BENCH" \
                --model "openai/$MODEL" \
                --no_sandbox \
                --max_connections 20 \
                "${LIMIT_ARGS[@]}" \
                2>&1 | tee -a "$RESULTS_LOG"; then
                echo "  >> $BENCH_NAME DONE: $(date)" | tee -a "$RESULTS_LOG"
            else
                echo "  >> $BENCH_NAME FAILED: $(date)" | tee -a "$RESULTS_LOG"
            fi
        )

        echo "" | tee -a "$RESULTS_LOG"
    done

    echo ">>> [$MODEL_NUM/$TOTAL] $MODEL complete" | tee -a "$RESULTS_LOG"
    echo "========================================" | tee -a "$RESULTS_LOG"
done

echo "" | tee -a "$RESULTS_LOG"
echo "=== All runs complete: $(date) ===" | tee -a "$RESULTS_LOG"
