# 🧬 GenHealthy

### A clinical agent that refuses to hallucinate — powered by Strands Decider 2B on Amazon Bedrock

![Strands Decider 2B](https://img.shields.io/badge/Strands_Decider-2B-ff9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-AgentCore-232f3e?style=for-the-badge&logo=amazonaws&logoColor=ff9900)
![Pattern](https://img.shields.io/badge/pattern-%23guardrails-3fb950?style=for-the-badge)
![CPU only](https://img.shields.io/badge/GPU-not_needed-3fb950?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT--0-yellow?style=for-the-badge)
![Tests](https://img.shields.io/badge/tests-40_passing-3fb950?style=for-the-badge)

> **The problem:** in genomics, a large language model that invents a gene, a variant or a risk claim isn't just wrong — it's dangerous.
> **The idea:** before any clinical statement reaches a physician, a tiny 2B decision model checks, with calibrated confidence, whether the cited sources actually back it up. Grounded claims pass. Unsupported ones are held for review. 🛡️

---

## ✨ What it does

GenHealthy reads multi-omic cardiometabolic reports (genetic variants, labs, anamnesis) and produces a **cross-reading** — statements linking genes, drugs and traits, each citing its source. A **Strands Decider 2B** model running on **Amazon Bedrock AgentCore** then audits every statement:

| Claim | Cited source | Decider P(supported) | Verdict |
|---|---|---|---|
| *FTO rs9939609 ↑ obesity risk* | FTO literature chunk | **0.8671** | ✅ passes |
| *BRCA1 drives this cardiometabolic risk* | FTO literature chunk | **0.4012** | 🚫 held for review |

Same model, two very different confidences — exactly the calibrated judgment a guardrail needs.

---

## 🏗️ Architecture

\`\`\`mermaid
flowchart TD
    U([👩‍⚕️ Clinician]) --> AG

    subgraph AGENT["🤖 Agent layer — the new part"]
        AG[Strands Agent]
        GATE{{🛡️ Grounding Gate}}
    end

    subgraph CORE["🧬 GenRisk clinical core — reused"]
        RAG[["🔎 Hybrid RAG<br/>FAISS vectors + rsid/gene lexical"]]
        GEN[["✍️ Cross-reading<br/>explicacao_service"]]
        XCHECK[["⚖️ Deterministic cross-check<br/>LOINC cutoffs"]]
    end

    subgraph AWS["☁️ Amazon Bedrock"]
        LLM[["🧠 Claude 3.5 Sonnet<br/>via Bedrock · generative"]]
        DEC[["🎯 Strands Decider 2B<br/>AgentCore Runtime · int8 CPU"]]
    end

    AG --> RAG
    RAG --> GEN
    GEN <--> LLM
    GEN --> XCHECK
    GEN --> GATE
    GATE -->|"noul: supported?"| DEC
    DEC -->|"calibrated P(yes)"| GATE
    GATE -->|"P ≥ 0.75 ✅"| OUT([📋 Grounded reading])
    GATE -->|"P < 0.75 🚫"| REV([⏸️ Held for review])

    classDef new fill:#1f6f43,stroke:#3fb950,color:#fff,stroke-width:2px;
    classDef aws fill:#232f3e,stroke:#ff9900,color:#fff,stroke-width:2px;
    classDef core fill:#1b2838,stroke:#4a9eff,color:#fff;
    class AG,GATE new;
    class LLM,DEC aws;
    class RAG,GEN,XCHECK core;
\`\`\`

**The flow in one breath:** the agent retrieves evidence (hybrid RAG), the generative model drafts the cross-reading, and *before it ships*, the Decider scores each claim against its cited sources. The gate **fails closed** — if the Decider is unreachable, nothing passes unaudited.

---

## 🎯 The decision we handed to Decider 2B

**Pattern:** `#guardrails` · **Question type:** `noul` (yes/no with calibrated probability)

> *"Is this clinical statement supported by the cited source excerpts?"*

Why a 2B decision model instead of asking the LLM to check itself:

- 🎚️ **Calibrated** — a P(yes) of 0.8 is right ~80% of the time, so the threshold is a real dial, not a vibe.
- ⚡ **Cheap & repeatable** — one tiny decision per statement, the high-frequency pattern where small models shine.
- 🧱 **Separation of concerns** — generation and judgment are different jobs, done by different models.

The reusable recipe lives in [`patterns/grounding_gate.md`](patterns/grounding_gate.md): the typed question, the option set, and the wiring — drop it into any agent that emits cited claims.

---

## 🔬 Why hybrid RAG matters here

Semantic similarity alone can rank a plausible-but-wrong source highly. In genomics, **variant identity can't be a vibe** — so retrieval combines FAISS vector scores with an exact `rsid`/`gene` lexical match. Sources that literally mention the cited variant rise to the top, and the Decider gets sharper evidence to judge.

---

## 🚀 Quickstart

\`\`\`bash
# build (ONNX embeddings, CPU-only — no torch, no CUDA)
docker build -t genhealthy ./backend

# run the gate against the live Decider on AgentCore
docker run --rm -e AWS_REGION=us-east-1 -v ~/.aws:/root/.aws:ro genhealthy \
  python -c "from genrisk_agent.grounding_gate import auditar_cruzamento; \
  v = auditar_cruzamento('FTO rs9939609 is associated with increased obesity risk.', \
  ['c1'], {'c1': 'FTO variant rs9939609 increases obesity and type 2 diabetes risk.'}); \
  print('P(supported)=', v.p_supported, 'ok=', v.ok)"
\`\`\`

---

## 🧰 Stack

- **Agent:** Strands Agents SDK
- **Generative:** Claude via Amazon Bedrock
- **Decision:** Strands Decider 2B on Bedrock AgentCore Runtime (int8, CPU)
- **Retrieval:** FAISS + sentence-transformers (ONNX/CPU) + lexical rsid/gene
- **Core:** FastAPI · deterministic LOINC cross-check · VCF/FHIR ingestion

---

## 📦 Reusable asset

`patterns/grounding_gate.md` + `genrisk_agent/grounding_gate.py` + `genrisk_agent/decider_client.py` — a self-contained guardrail you can lift into your own Strands agent.

---

<div align="center">

**Built for the Strands Decider 2B hackathon** · `#strands-decider-2b` `#guardrails`

🧬 *Grounded by design.*

</div>