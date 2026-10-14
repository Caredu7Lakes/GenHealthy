"""GenHealthy agent (Strands + Bedrock). Grounding decision delegated to
Decider 2B via the gate (see tools.leitura_cruzada_auditada)."""
from __future__ import annotations
import os
from strands import Agent
from strands.models import BedrockModel
from .tools import leitura_cruzada_auditada

SYSTEM = ("You are a clinical reading-support agent. Use the audited "
          "cross-reading tool and never assert anything beyond what it "
          "returns as grounded.")


def build_agent() -> Agent:
    model = BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    return Agent(model=model, system_prompt=SYSTEM, tools=[leitura_cruzada_auditada])


if __name__ == "__main__":
    print(build_agent()("Produce the audited cross-reading for patient 001."))
