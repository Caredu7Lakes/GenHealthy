# Grounding Gate — a reusable Strands Decider 2B pattern

**Tags:** `#strands-decider-2b` `#guardrails`

## What it is
A **per-statement semantic grounding gate**. For every claim an LLM generates
with cited sources, it asks a Strands Decider 2B — running on Amazon Bedrock
AgentCore — whether the cited excerpts actually support that claim. The answer
is a calibrated probability, so a threshold is a real dial, not a guess.

It complements, never replaces, deterministic checks. Keep structural validation
("is there a source at all?") and numeric checks deterministic; hand the Decider
the semantic judgment "do these sources support this statement?".

## The typed decision
- **Question type:** `noul` (yes/no, returns a calibrated P(yes))
- **Question:** *"Is this clinical statement supported by the cited source excerpts?"*
- **State sent to the Decider:** the statement + its cited source excerpts
- **Block rule:** `ok = P(yes) >= GROUNDING_THRESHOLD` (default 0.75)
- **Fail-closed:** if the Decider is unreachable, the statement is held for review
  (never passes unaudited)

## Measured behaviour (real Decider on AgentCore)
| Statement | Cited source | P(supported) | Verdict |
|---|---|---|---|
| FTO rs9939609 ↑ obesity risk | FTO literature chunk | 0.8671 | ✅ pass |
| BRCA1 drives this cardiometabolic risk | FTO literature chunk | 0.4012 | 🚫 review |

## How to wire it
Two files make the asset portable: `genrisk_agent/decider_client.py` (the
official MIT-0 strands-decider client) and `genrisk_agent/grounding_gate.py`.

```python
from genrisk_agent.grounding_gate import (
    construir_mapa_fontes, auditar_leitura,
)

# 1. map each source id -> its text (from your retrieval step)
mapa = construir_mapa_fontes(chunks, laudo_contexto=context)

# 2. audit a whole reading: annotates each statement and adds a summary
result = auditar_leitura(result, mapa)          # threshold from config
# result["grounding_gate"]["status"]  -> "ok" | "needs_review"
# result["cruzamentos"][i]["grounding"] -> {"p_supported": float, "ok": bool}
```

Single-statement form:

```python
from genrisk_agent.grounding_gate import auditar_cruzamento

v = auditar_cruzamento(statement, source_ids, mapa)   # -> Verdict(p_supported, ok)
```

## Configuration
Set in `app/core/config.py` (or environment):

| setting | meaning |
|---|---|
| `DECIDER_ARN` | the AgentCore runtime ARN of your deployed Decider |
| `GROUNDING_THRESHOLD` | P(yes) floor for a statement to pass (default 0.75) |
| `AWS_REGION` | region of the runtime (us-east-1) |

Auth is SigV4/IAM: the caller needs `bedrock-agentcore:InvokeAgentRuntime` on
the runtime. No endpoint secret, no API key.

## Adapt to another domain
Swap the `QUESTION` string and the state you build in `auditar_cruzamento`. The
skeleton — typed `noul` question + evidence map + threshold + fail-closed — fits
any agent that emits cited claims. For a decision with named options instead of
yes/no, switch the Decider question type to `choice` (see `decider_client.py`:
`noul`, `choice`, `score`).

## Why a 2B decision model, not the LLM itself
- **Calibrated** — P(yes)=0.8 is right ~80% of the time; the threshold means something.
- **Cheap & repeatable** — one tiny decision per statement; the high-frequency
  pattern where small decision models pay off.
- **Separation of concerns** — generation and judgment are different jobs.

## Dependencies
- `genrisk_agent/decider_client.py` — official strands-decider client (MIT-0, boto3).
- Decider 2B deployed on Amazon Bedrock AgentCore Runtime (int8, CPU).
- Generative model via Amazon Bedrock.