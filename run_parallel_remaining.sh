#!/usr/bin/env bash
# Run remaining 12 models in 4 parallel streams via OpenRouter.
# Usage: ./run_parallel_remaining.sh [--limit N]
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

run_model_stream() {
    local STREAM_NAME="$1"
    shift
    local MODELS=("$@")
    local LOG="$SCRIPT_DIR/results/run_log_parallel_${STREAM_NAME}_$(date +%Y%m%d_%H%M%S).txt"

    echo "=== Stream $STREAM_NAME started: $(date) ===" | tee "$LOG"

    for MODEL in "${MODELS[@]}"; do
        echo ">>> [$STREAM_NAME] Model: $MODEL" | tee -a "$LOG"

        local BENCH_IDX=0
        for BENCH in "${BENCHMARKS[@]}"; do
            local BENCH_NAME="${BENCHMARK_NAMES[$BENCH_IDX]}"
            BENCH_IDX=$((BENCH_IDX + 1))

            # Skip Moral Circuits for non-Qwen/Llama models
            if [[ "$BENCH_NAME" == "MoralCircuits" ]]; then
                case "$MODEL" in
                    qwen/*|meta-llama/*) ;;
                    *)
                        echo "  >> $BENCH_NAME SKIPPED (not applicable): $(date)" | tee -a "$LOG"
                        continue
                        ;;
                esac
            fi

            echo "  >> $BENCH_NAME ($BENCH)" | tee -a "$LOG"
            echo "  >> Started: $(date)" | tee -a "$LOG"

            (
                cd "$SCRIPT_DIR/src/inspect"
                if uv run --package cei-inspect python run.py \
                    --tasks "$BENCH" \
                    --model "openai/$MODEL" \
                    --no_sandbox \
                    --max_connections 20 \
                    "${LIMIT_ARGS[@]}" \
                    2>&1 | tee -a "$LOG"; then
                    echo "  >> $BENCH_NAME DONE: $(date)" | tee -a "$LOG"
                else
                    echo "  >> $BENCH_NAME FAILED: $(date)" | tee -a "$LOG"
                fi
            )

            echo "" | tee -a "$LOG"
        done

        echo ">>> [$STREAM_NAME] $MODEL complete: $(date)" | tee -a "$LOG"
        echo "========================================" | tee -a "$LOG"
    done

    echo "=== Stream $STREAM_NAME complete: $(date) ===" | tee "$LOG"
}

echo "=== Launching 4 parallel streams: $(date) ==="

# Stream 1: DeepSeek family
run_model_stream "deepseek" \
    "deepseek/deepseek-r1-distill-llama-70b" \
    "deepseek/deepseek-chat-v3.1" \
    "deepseek/deepseek-r1" &
PID1=$!

# Stream 2: Llama family
run_model_stream "llama" \
    "meta-llama/llama-3.2-3b-instruct" \
    "meta-llama/llama-3.1-8b-instruct" \
    "meta-llama/llama-3.3-70b-instruct" &
PID2=$!

# Stream 3: Gemma family
run_model_stream "gemma" \
    "google/gemma-3-4b-it" \
    "google/gemma-3-12b-it" \
    "google/gemma-3-27b-it" &
PID3=$!

# Stream 4: MiniMax family
run_model_stream "minimax" \
    "minimax/minimax-01" \
    "minimax/minimax-m1" \
    "minimax/minimax-m2.5" &
PID4=$!

echo "Stream PIDs: deepseek=$PID1 llama=$PID2 gemma=$PID3 minimax=$PID4"
echo "Logs: results/run_log_parallel_*.txt"

wait $PID1 $PID2 $PID3 $PID4
echo "=== All streams complete: $(date) ==="
