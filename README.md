# 🧬 GenHealthy

### A multi-agent clinical pipeline that refuses to hallucinate — powered by Strands Decider 2B on Amazon Bedrock

![Strands Decider 2B](https://img.shields.io/badge/Strands_Decider-2B-ff9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-AgentCore-232f3e?style=for-the-badge&logo=amazonaws&logoColor=ff9900)
![Nova Pro](https://img.shields.io/badge/Nova_Pro-vision-6b3fa0?style=for-the-badge)
![Pattern](https://img.shields.io/badge/pattern-%23guardrails-3fb950?style=for-the-badge)
![CPU only](https://img.shields.io/badge/GPU-not_needed-3fb950?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT--0-yellow?style=for-the-badge)
![Tests](https://img.shields.io/badge/tests-40_passing-3fb950?style=for-the-badge)

> **The problem:** in clinical AI, a model that invents a gene or a finding isn't just wrong — it's dangerous. And a pipeline that ships a verdict while a model silently failed is worse.
> **The idea:** a tiny 2B decision model makes three calibrated judgments across the pipeline — and the pipeline **refuses to produce a verdict unless every model in the loop actually ran.** 🛡️

---

## ✨ What it does

A patient sends an **ECG report + image** and their clinical data over a (mocked) confidential channel. GenHealthy runs a multi-agent pipeline and hands the doctor a single **final position** to validate — or tells the doctor plainly that a model did not analyze, and produces no verdict at all.

Three decisions go to **Strands Decider 2B** (on Amazon Bedrock AgentCore):

| # | Decision | Type | What it catches |
|---|---|---|---|
| 1 | Is each clinical statement grounded in its cited sources? | `noul` | hallucinated claims |
| 2 | Does the ECG report match what the ECG image shows? | `choice` | report ↔ image conflict |
| 3 | Is the current analysis consistent with prior validated history? | `choice` | silent clinical drift |

Measured on the live Decider:

| Claim | Cited source | Decider P(supported) | Verdict |
|---|---|---|---|
| *FTO rs9939609 ↑ obesity risk* | FTO literature chunk | **0.8671** | ✅ passes |
| *BRCA1 drives this cardiometabolic risk* | FTO literature chunk | **0.4012** | 🚫 held for review |

Same model, two very different confidences — exactly the calibrated judgment a guardrail needs.

---

## 🏗️ Architecture

\`\`\`mermaid
flowchart TD
    P([👤 Patient]) -->|report + image, sealed| ENV[🔒 Envelope<br/>symbolic encryption + password]
    ENV --> INPUTS

    subgraph INPUTS["📥 Patient inputs"]
        L1[/"🧬 Genetic · labs · anamnesis"/]
        L4[/"🫀 ECG report + image"/]
    end

    L4 --> V[["👁️ Agent 1 — Nova Pro<br/>reads ECG image → findings"]]
    L1 --> GEN[["✍️ Cross-reading<br/>Claude · hybrid RAG"]]

    GEN --> D1{{"🛡️ Decider — grounding<br/>each claim vs sources"}}
    V --> D2{{"🎯 Decider — ECG conformity<br/>conforme / não / inconclusivo"}}
    L4 --> D2

    D1 --> GATE
    D2 --> GATE
    subgraph GATE["⚖️ Integrity gate + consolidation"]
        FP["No final position unless<br/>BOTH models ran.<br/>Deterministic fusion → status"]
    end

    FP --> HIST{{"📚 Decider — history check<br/>vs prior records · only if history exists"}}
    HIST --> MED([👩‍⚕️ Doctor validates / rejects])
    MED -->|validated only| DB[("🗄️ DynamoDB<br/>medical history")]
    DB -.->|feeds next visit| HIST

    classDef v fill:#6b3fa0,stroke:#b084e8,color:#fff,stroke-width:2px;
    classDef aws fill:#232f3e,stroke:#ff9900,color:#fff,stroke-width:2px;
    classDef gate fill:#1f6f43,stroke:#3fb950,color:#fff,stroke-width:2px;
    class V v;
    class D1,D2,HIST aws;
    class GATE,FP gate;
\`\`\`

**The flow in one breath:** Nova Pro reads the ECG image, Claude drafts the cross-reading over hybrid RAG, and the Decider judges three times — grounding, ECG conformity, and consistency with history. The gate **fails closed**: if any model didn't run, no verdict ships.

---

## 🛡️ The integrity gate — the part we're proudest of

A clinical pipeline must never emit a verdict on partial analysis. GenHealthy's gate **fails closed**: if Nova Pro (vision) or Claude (reading) did not run — a daily token quota, a network error — the pipeline returns `pipeline_incompleto` **naming the missing model**, and produces no final position. The doctor sees *"Nova Pro did not analyze"*, never a verdict built on half the evidence.

---

## 🎯 The decisions we handed to Decider 2B

**Pattern:** `#guardrails`. Three calibrated judgments, each one typed:

1. **Grounding** (`noul`) — *"Is this clinical statement supported by the cited source excerpts?"* → P(yes), blocks below 0.75.
2. **ECG conformity** (`choice`) — *"Does the ECG report match the image findings?"* → conforme / não_conforme / inconclusivo.
3. **History check** (`choice`) — *"Is the current analysis consistent with prior validated history?"* → consistente / evolução esperada / conflito. Runs only when history exists; informative, never blocks.

Why a 2B decision model instead of asking the LLM to check itself:

- 🎚️ **Calibrated** — a P(yes) of 0.8 is right ~80% of the time, so the threshold is a real dial, not a vibe.
- ⚡ **Cheap & repeatable** — one tiny decision per judgment, the high-frequency pattern where small models shine.
- 🧱 **Separation of concerns** — generation, vision and judgment are different jobs, done by different models.

The reusable recipe lives in [`patterns/grounding_gate.md`](patterns/grounding_gate.md): the typed question, the option set, and the wiring — drop it into any agent that emits cited claims.

---

## 🔐 Security & confidentiality

The patient channel is modeled after a real confidential exchange:

- **Sealed envelope** — every document the patient sends is wrapped (`encrypted: true`) and opens only with the right **password** (hash-checked). The anamnesis the doctor sends back carries its own password for the patient to open.
- **Symbolic, not production crypto** — this encodes the *confidentiality flow* for the demo; it is not a real cipher, and we say so plainly rather than overclaim.
- **Least-privilege IAM** — DynamoDB access is scoped to the single history table; the Decider is called over IAM/SigV4 (`bedrock-agentcore:InvokeAgentRuntime`), no endpoint secret in the image.

---

## 🔬 Why hybrid RAG matters here

Semantic similarity alone can rank a plausible-but-wrong source highly. In genomics, **variant identity can't be a vibe** — so retrieval combines FAISS vector scores with an exact `rsid`/`gene` lexical match. Sources that literally mention the cited variant rise to the top, and the Decider gets sharper evidence to judge.

---

## 🚀 Quickstart

\`\`\`bash
# build (ONNX embeddings, CPU-only — no torch, no CUDA)
docker build -t genhealthy ./backend

# run the grounding gate against the live Decider on AgentCore
docker run --rm -e AWS_REGION=us-east-1 -v ~/.aws:/root/.aws:ro genhealthy \
  python -c "from genrisk_agent.grounding_gate import auditar_cruzamento; \
  v = auditar_cruzamento('FTO rs9939609 is associated with increased obesity risk.', \
  ['c1'], {'c1': 'FTO variant rs9939609 increases obesity and type 2 diabetes risk.'}); \
  print('P(supported)=', v.p_supported, 'ok=', v.ok)"
\`\`\`

---

## 🧰 Stack

- **Agents:** Strands Agents SDK · Amazon Nova Pro (vision) · Claude via Bedrock (generative)
- **Decisions:** Strands Decider 2B on Bedrock AgentCore Runtime (int8, CPU)
- **Retrieval:** FAISS + sentence-transformers (ONNX/CPU) + lexical rsid/gene hybrid
- **History:** Amazon DynamoDB (written only on doctor validation)
- **Core:** FastAPI · deterministic LOINC cross-check · VCF/FHIR ingestion · React frontend

---

## 📦 Reusable asset

`patterns/grounding_gate.md` + `genrisk_agent/grounding_gate.py` + `genrisk_agent/decider_client.py` — a self-contained guardrail you can lift into your own Strands agent.

---

<div align="center">

**Built for the Strands Decider 2B hackathon** · `#strands-decider-2b` `#guardrails`

🧬 *Three decisions. One honest pipeline.*

</div>