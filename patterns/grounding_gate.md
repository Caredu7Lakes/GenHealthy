# Grounding Gate — a reusable Strands Decider 2B pattern

**Tags:** `#strands-decider-2b` `#guardrails`

## What it is
A **per-item semantic grounding gate**: for every statement an LLM generates
with cited sources, it asks Decider 2B whether the cited excerpts actually
support that statement. A typed, high-frequency decision (one per statement) —
exactly where a small decision model beats having the LLM re-check itself on
cost and latency.

It complements, not replaces, deterministic checks. Keep structural validation
("is there a source at all?") and numeric checks deterministic; hand Decider the
semantic judgment "does the source support the claim?".

## Typed question
- **Question:** "Is the clinical statement supported by the cited source excerpts?"
- **Options:** `supported` | `unsupported` | `contradicted`
- **Block rule:** `unsupported`/`contradicted` with `confidence >= threshold` (default 0.7)

## How to wire it
1. Build an `id -> text` map with `construir_mapa_fontes(chunks, laudo_contexto)`.
2. Audit one item with `auditar_cruzamento(statement, sources, map, threshold)`, or
3. Audit a whole response with `auditar_leitura(result, map)`, which annotates each
   item with `grounding` and adds a `grounding_gate` summary (`ok` / `needs_review`).

```python
from genrisk_agent.grounding_gate import construir_mapa_fontes, auditar_leitura

mapa = construir_mapa_fontes(chunks, laudo_contexto=context)
result = auditar_leitura(result, mapa, threshold=0.7)
# result["grounding_gate"]["status"] == "ok" | "needs_review"
```

## Adapt to another domain
Swap `QUESTION`/`OPTIONS` and the context format passed to `decide()`. The same
skeleton — typed question + evidence map + threshold — fits any agent that emits
cited statements.

## Dependencies
- `genrisk_agent/decider.py` — Decider 2B client (endpoint via `DECIDER_ENDPOINT`).
- Generative model via Amazon Bedrock (`app.core.llm.BedrockClient`, `LLM_PROVIDER=bedrock`).