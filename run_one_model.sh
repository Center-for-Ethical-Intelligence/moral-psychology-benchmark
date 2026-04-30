#!/usr/bin/env bash
# Run all benchmarks for a single model.
# Usage: ./run_one_model.sh <model_id>
# Example: ./run_one_model.sh deepseek/deepseek-r1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

export OPENAI_API_KEY="$(grep OPENROUTER_API_KEY "$SCRIPT_DIR/.env" | cut -d= -f2)"
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export MOREBENCH_DATA_DIR="$SCRIPT_DIR/data/morebench"
export MORAL_CIRCUITS_DATA_DIR="$SCRIPT_DIR/data/moral_circuits"
export M3ORAL_DATA_DIR="$SCRIPT_DIR/data/m3oralbench"
export MORALLENS_DATA_DIR="$SCRIPT_DIR/data/morallens"

MODEL="$1"
SLUG=$(echo "$MODEL" | tr '/' '_')
LOG="$SCRIPT_DIR/results/run_log_${SLUG}_$(date +%Y%m%d_%H%M%S).txt"

echo "=== $MODEL started: $(date) ===" | tee "$LOG"

run_bench() {
    local BENCH="$1" BENCH_NAME="$2"
    echo "  >> $BENCH_NAME started: $(date)" | tee -a "$LOG"
    (
        cd "$SCRIPT_DIR/src/inspect"
        uv run --package cei-inspect python run.py \
            --tasks "$BENCH" \
            --model "openai/$MODEL" \
            --no_sandbox \
            --max_connections 50 \
            2>&1 | tee -a "$LOG"
    )
    echo "  >> $BENCH_NAME finished: $(date)" | tee -a "$LOG"
    echo "" | tee -a "$LOG"
}

run_bench "evals/morebench.py" "MoReBench"

# Moral Circuits only for Qwen/Llama
case "$MODEL" in
    qwen/*|meta-llama/*) run_bench "evals/moral_circuits.py" "MoralCircuits" ;;
    *) echo "  >> MoralCircuits SKIPPED" | tee -a "$LOG" ;;
esac

run_bench "evals/m3oralbench.py" "M3oralBench"
run_bench "evals/morallens.py" "MoralLens"

echo "=== $MODEL complete: $(date) ===" | tee -a "$LOG"
