# CEI Moral-Psych Benchmark — Joseph's Progress Report

**Report owner:** Joseph Sun
**Last updated:** April 30, 2026
**Branch:** `joseph/remaining-benchmarks`

---

## Benchmark Harness Status

| # | Benchmark | Paper | Harness File | Status | Tasks |
|---|-----------|-------|--------------|--------|-------|
| 1 | **TrolleyBench** | Zhu 2025 | `run_trolleybench.py` | **Complete** | Multi-turn ethical consistency (ECI, entropy, reversal rate) |
| 2 | **MoReBench** | Chiu 2025 | `src/inspect/evals/morebench.py` | **Complete** | `morebench_advisor`, `morebench_agent` |
| 3 | **Moral Circuits** | Schacht 2025 | `src/inspect/evals/moral_circuits.py` | **Complete** | `moral_circuits_judgment`, `moral_circuits_reasoning` |
| 4 | **M³oralBench** | Yan 2024 | `src/inspect/evals/m3oralbench.py` | **Complete** | `m3oralbench_judgment`, `m3oralbench_foundation`, `m3oralbench_response` |
| 5 | **MoralLens** | Samway 2025 | `src/inspect/evals/morallens.py` | **Complete** | `morallens_cot`, `morallens_posthoc`, `morallens_double_standard`, `morallens_reasoning_quality` |

---

## Family-Size Progress Matrix

| Line | TrolleyBench | MoReBench | Moral Circuits | M³oralBench | MoralLens | Note |
| :--- | :---: | :---: | :---: | :---: | :---: | --- |
| `Qwen-S` (Qwen3-8B) | **Done** | **Done** | **Done** | **Partial** | **Done** | ML: cot=0.921, ds=0.378, ph=0.887; M3: fnd=0.047, jdg+rsp=error |
| `Qwen-M` (Qwen3-32B) | **Done** | **Done** | **Done** | **Done** | **Done** | ML: cot=0.243, ds=0.103, ph=0.307 |
| `Qwen-L` (Qwen3-235B) | **Done** | **Done** | **Done** | **Partial** | Queue | MRB: adv=0.611, agt=0.587; MC: jdg=0.933, rsn=0.938; M3: fnd=0.035, jdg=0.483, rsp=credit_err |
| `DeepSeek-S` (R1-Distill-70B) | **Done** | Queue | Queue | Queue | Queue | |
| `DeepSeek-M` (Chat V3.1) | **Done** | Queue | Queue | Queue | Queue | |
| `DeepSeek-L` (DeepSeek-R1) | **Done** | Queue | Queue | Queue | Queue | |
| `Llama-S` (Llama-3.2-3B) | **Done** | Queue | **Queue** | Queue | Queue | Moral Circuits requires open-weight |
| `Llama-M` (Llama-3.1-8B) | **Done** | Queue | **Queue** | Queue | Queue | Moral Circuits requires open-weight |
| `Llama-L` (Llama-3.3-70B) | **Done** | Queue | **Queue** | Queue | Queue | Moral Circuits requires open-weight |
| `Gemma-S` (Gemma-3-4B) | **Done** | Queue | N/A | Queue | Queue | Moral Circuits: Llama/Qwen only |
| `Gemma-M` (Gemma-3-12B) | **Done** | Queue | N/A | Queue | Queue | Moral Circuits: Llama/Qwen only |
| `Gemma-L` (Gemma-3-27B) | **Done** | Queue | N/A | Queue | Queue | Moral Circuits: Llama/Qwen only |
| `MiniMax-S` (MiniMax-01) | **Done** | Queue | N/A | Queue | Queue | Moral Circuits: Llama/Qwen only |
| `MiniMax-M` (MiniMax-M1) | **Done** | Queue | N/A | Queue | Queue | Moral Circuits: Llama/Qwen only |
| `MiniMax-L` (MiniMax-M2.5) | **Done** | Queue | N/A | Queue | Queue | Moral Circuits: Llama/Qwen only |

---

## Run Configuration

- **API:** OpenRouter (all model IDs verified against live API on April 21, 2026)
- **Temperatures:** 0.0 and 0.7
- **Harness:** Inspect AI (`@task` pattern) for MoReBench, Moral Circuits, M³oralBench, MoralLens
- **Harness:** Custom multi-turn for TrolleyBench (`run_trolleybench.py`)
- **Per TrolleyBench model:** 18 scenarios × 3 turns = 54 API calls
- **Total TrolleyBench:** 15 models × 2 temps × 54 calls = 1,620 API calls

---

## Completed Results (TrolleyBench)

### Preliminary Metrics

| Line | ECI | Entropy Inconsistency | Reversal Rate | Dominant Framework |
| :--- | ---: | ---: | ---: | --- |
| `Qwen-L T=0.0` | 0.714 | 0.333 | 0.0% | consequentialist |
| `Qwen-L T=0.7` | 0.714 | 0.177 | 10.0% | mixed |
| `Qwen-M T=0.0` | 0.750 | 0.059 | 10.0% | deontological |

### Variant-Level Actions (T1 initial response)

| Line | Switch | Footbridge | Loop | Trapdoor | Man-in-front | Saboteur | Organ | Self-sacrifice | AV | Bystander |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Qwen-L T=0.0` | act | act | act | no_act | - | act | - | act | - | act |
| `Qwen-L T=0.7` | act | no_act | act | act | - | act | - | act | - | act |
| `Qwen-M T=0.0` | act | act | act | act | no_act | act | - | act | - | act |

### Key Observations

- **Larger models resist persuasion** — Qwen-L T=0.0 shows 0% reversal rate vs 10% for Qwen-M
- **Temperature degrades consistency** — T=0.7 causes framework mixing and higher reversal rates
- **Footbridge is the cracking point** — physically-direct push variant breaks consequentialism first
- **Same actions, different frameworks** — Qwen-M frames similar decisions via deontology vs Qwen-L's consequentialism

---

## Benchmark Design Notes

### MoReBench
- 500 core scenarios + 150 framework-specific variants
- Two roles: advisor (external guidance) vs agent (first-person decision)
- Scored against 4 rubric dimensions: identification, logic, process_clarity, outcome
- Keyword-based presence scoring for each dimension

### Moral Circuits
- Requires open-weight models for activation recording (Llama 3, Qwen 2.5 only)
- Two tasks: judgment accuracy (acceptable/unacceptable) + foundation identification
- Statement pairs: matched moral/immoral pairs per foundation concept
- Ablation assessment: reasoning quality after conceptual perturbation

### M³oralBench
- 1,160 AI-generated image scenarios mapped to MFT foundations
- Three tasks: moral judgment, foundation classification, response generation
- Supports multimodal (image) and text-only fallback
- VLMs required for full image evaluation

### MoralLens
- 600+ dilemmas under two conditions
- **CoT condition:** think-then-decide (expected: deontological reasoning)
- **Post-hoc condition:** decide-then-explain (expected: consequentialist reasoning)
- Double-standard scorer detects the systematic framework shift
- 16 rationale types (8 consequentialist + 8 deontological)

---

## Environment Variables

| Variable | Required By | Description |
|----------|-------------|-------------|
| `MOREBENCH_DATA_DIR` | MoReBench | Path to MoReBench JSON/JSONL files |
| `MORAL_CIRCUITS_DATA_DIR` | Moral Circuits | Path to statement pair files |
| `M3ORAL_DATA_DIR` | M³oralBench | Path to images/ + annotations |
| `MORALLENS_DATA_DIR` | MoralLens | Path to dilemma files |

---

## Model Families and Routes

| Family | Small | Medium | Large |
| --- | --- | --- | --- |
| `Qwen` | `qwen/qwen3-8b` | `qwen/qwen3-32b` | `qwen/qwen3-235b-a22b` |
| `DeepSeek` | `deepseek/deepseek-r1-distill-llama-70b` | `deepseek/deepseek-chat-v3.1` | `deepseek/deepseek-r1` |
| `Llama` | `meta-llama/llama-3.2-3b-instruct` | `meta-llama/llama-3.1-8b-instruct` | `meta-llama/llama-3.3-70b-instruct` |
| `Gemma` | `google/gemma-3-4b-it` | `google/gemma-3-12b-it` | `google/gemma-3-27b-it` |
| `MiniMax` | `minimax/minimax-01` | `minimax/minimax-m1` | `minimax/minimax-m2.5` |

All routes via OpenRouter. Model IDs verified against live API on April 21, 2026.

---

## Status Key

| Mark | Meaning |
| --- | --- |
| **Done** | Finished with usable results at both temperatures |
| **Live** | Currently running |
| **Queue** | Harness ready, awaiting execution |
| **N/A** | Benchmark not applicable to this model family |

---

## Snapshot

| Field | Value |
| --- | --- |
| Harnesses complete | 5 / 5 |
| TrolleyBench cells completed | 30 / 30 (all 15 models × 2 temps) |
| MoReBench cells completed | 3 / 15 (Qwen-L best: adv=0.611, agt=0.587) |
| Moral Circuits cells completed | 3 / 6 (Qwen-S: 0.929; Qwen-M: 0.192; Qwen-L: 0.933) |
| M³oralBench cells completed | 1 / 15 (Qwen-M: fnd=0.012, jdg=0.076, rsp=0.005; Qwen-S+L partial) |
| MoralLens cells completed | 2 / 15 (Qwen-S: cot=0.921; Qwen-M: cot=0.243) |
| Group plan target | 5 benchmarks × 5 families × 3 sizes = 75 cells |
| Blocker | OpenRouter credits exhausted (402 error). Need credit top-up to continue. |
| Next step | Top up credits, then run run_parallel_remaining.sh (4 streams, max_connections=20) |
