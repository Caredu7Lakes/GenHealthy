"""Agente GenHealthy (Strands + Bedrock). Decisão de grounding delegada ao
Decider 2B via gate (ver tools.leitura_cruzada_auditada)."""
from __future__ import annotations
import os
from strands import Agent                      # confirmar imports contra o SDK
from strands.models import BedrockModel
from .tools import leitura_cruzada_auditada

SYSTEM = ("Você é um agente de apoio à leitura clínica. Use a tool de leitura "
          "cruzada auditada e nunca afirme além do que ela retornar como grounded.")

def build_agent() -> Agent:
    model = BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    return Agent(model=model, system_prompt=SYSTEM, tools=[leitura_cruzada_auditada])

if __name__ == "__main__":
    print(build_agent()("Faça a leitura cruzada auditada do paciente 001."))