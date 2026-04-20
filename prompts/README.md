# Prompts

Place benchmark prompt files here as JSONL (one JSON object per line).

## Format

```jsonl
{"id": "001", "prompt": "Is it morally permissible to divert the trolley?", "metadata": {"category": "trolley"}}
{"id": "002", "system": "You are a moral advisor.", "prompt": "Evaluate this dilemma...", "metadata": {"framework": "deontological"}}
```

## Fields

- `id` (required) — unique prompt identifier
- `prompt` (required) — the user message
- `system` (optional) — system message for role-based benchmarks
- `metadata` (optional) — any extra info for analysis (category, framework, etc.)

## File Naming

Name files by benchmark ID from `config.py`:

```
prompts/morebench.jsonl
prompts/trolleybench.jsonl
prompts/morallens.jsonl
...
```
