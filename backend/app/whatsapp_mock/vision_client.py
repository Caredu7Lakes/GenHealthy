"""Agente de visao (Amazon Nova Pro via Bedrock converse).
Retorna VisionResult com ran=False se o modelo nao analisou (ex. cota),
para a trava de integridade do pipeline."""
from __future__ import annotations
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError
from app.core.config import get_settings

PROMPT = ("You are a cardiology support agent. Describe ONLY what the ECG trace "
          "shows: rhythm (regular/irregular), presence of P waves, approximate "
          "rate, and any visible abnormality. Do not read any report. Be concise.")


@dataclass
class VisionResult:
    ran: bool
    findings: str
    error: str = ""


def analisar_ecg(imagem_png: bytes) -> VisionResult:
    s = get_settings()
    client = boto3.client("bedrock-runtime", region_name=s.AWS_REGION)
    try:
        resp = client.converse(
            modelId=s.VISION_MODEL_ID,
            messages=[{"role": "user", "content": [
                {"image": {"format": "png", "source": {"bytes": imagem_png}}},
                {"text": PROMPT},
            ]}],
            inferenceConfig={"maxTokens": 400, "temperature": 0},
        )
        texto = resp["output"]["message"]["content"][0]["text"]
        return VisionResult(ran=True, findings=texto)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        return VisionResult(ran=False, findings="", error=code)
