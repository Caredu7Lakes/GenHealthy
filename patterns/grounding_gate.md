# Grounding Gate — a reusable Strands Decider 2B pattern

**Tags:** `#strands-decider-2b` `#guardrails`

## What it is
A **per-item judgment gate**: for every claim an agent produces, a Strands
Decider 2B — running on Amazon Bedrock AgentCore — gives a calibrated verdict
before the claim reaches a human. The answer is a probability, so a threshold is
a real dial, not a guess.

It complements, never replaces, deterministic checks. Keep structural validation
("is there a source at all?") and numeric checks deterministic; hand the Decider
the semantic judgment.

## Three places GenHealthy uses it

The same recipe — typed question, option set, evidence in the state, calibrated
answer — drives three decisions in one pipeline:

| # | Question | Type | Options / output |
|---|---|---|---|
| 1 | Is this clinical statement supported by the cited source excerpts? | `noul` | P(yes); block below threshold |
| 2 | Does the ECG report match what the ECG image shows? | `choice` | conforme / nao_conforme / inconclusivo |
| 3 | Is the current analysis consistent with the patient's prior validated history? | `choice` | consistente / evolucao_esperada / conflito_com_historico |

Decision 1 is the grounding gate below. Decisions 2 and 3 reuse the identical
client and wiring with a different typed question — that is the point of the
pattern: swap the question, keep the machinery.

## The grounding decision (decision 1)
- **Question type:** `noul` (yes/no, returns a calibrated P(yes))
- **Question:** *"Is this clinical statement supported by the cited source excerpts?"*
- **State sent to the Decider:** the statement + its cited source excerpts
- **Block rule:** `ok = P(yes) >= GROUNDING_THRESHOLD` (default 0.75)
- **Fail-closed:** if the Decider is unreachable, the statement is held for review

## Measured behaviour (real Decider on AgentCore)
| Statement | Cited source | P(supported) | Verdict |
|---|---|---|---|
| FTO rs9939609 ↑ obesity risk | FTO literature chunk | 0.8671 | ✅ pass |
| BRCA1 drives this cardiometabolic risk | FTO literature chunk | 0.4012 | 🚫 review |

## How to wire it
Two files make the asset portable: `genrisk_agent/decider_client.py` (the
official MIT-0 strands-decider client) and `genrisk_agent/grounding_gate.py`.

```python
from genrisk_agent.grounding_gate import construir_mapa_fontes, auditar_leitura

mapa = construir_mapa_fontes(chunks, laudo_contexto=context)
result = auditar_leitura(result, mapa)           # threshold from config
# result["grounding_gate"]["status"]  -> "ok" | "needs_review"
# result["cruzamentos"][i]["grounding"] -> {"p_supported": float, "ok": bool}
```

Single-statement form:

```python
from genrisk_agent.grounding_gate import auditar_cruzamento
v = auditar_cruzamento(statement, source_ids, mapa)   # -> Verdict(p_supported, ok)
```

For a `choice` decision (decisions 2 and 3), the same client exposes `choice`:

```python
from genrisk_agent.decider_client import DeciderClient, choice
r = DeciderClient(arn=DECIDER_ARN).decide(state, {"q": choice(question, options)})
r["answers"]["q"]["choice"]   # the picked option, with per-option probabilities
```

## Configuration
Set in `app/core/config.py` (or environment):

| setting | meaning |
|---|---|
| `DECIDER_ARN` | the AgentCore runtime ARN of your deployed Decider |
| `GROUNDING_THRESHOLD` | P(yes) floor for a statement to pass (default 0.75) |
| `AWS_REGION` | region of the runtime |

Auth is SigV4/IAM: the caller needs `bedrock-agentcore:InvokeAgentRuntime` on
the runtime. No endpoint secret, no API key.

## Security note
In GenHealthy the gate sits behind a confidential patient channel: documents
arrive sealed in a password-checked envelope (symbolic in the demo, not a real
cipher), and the runtime's IAM is least-privilege — DynamoDB history access is
scoped to a single table, the Decider is reached over SigV4. The gate itself
holds no credentials and the state it sends is only the claim plus its evidence.

## Adapt to another domain
Swap the `QUESTION` string and the state you build. The skeleton — typed
question + evidence + threshold + fail-closed — fits any agent that emits claims
to be judged. For named options instead of yes/no, switch the question type to
`choice` (see `decider_client.py`: `noul`, `choice`, `score`).

## Why a 2B decision model, not the LLM itself
- **Calibrated** — P(yes)=0.8 is right ~80% of the time; the threshold means something.
- **Cheap & repeatable** — one tiny decision per item; the high-frequency pattern.
- **Separation of concerns** — generation and judgment are different jobs.

## Dependencies
- `genrisk_agent/decider_client.py` — official strands-decider client (MIT-0, boto3).
- Decider 2B deployed on Amazon Bedrock AgentCore Runtime (int8, CPU).
- Generative via Amazon Bedrock; vision via Amazon Nova Pro.