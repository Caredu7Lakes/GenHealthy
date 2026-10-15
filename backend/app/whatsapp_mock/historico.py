"""Historico medico em DynamoDB + confronto atual x historico via Decider 2B.

- registrar(): grava no historico SO quando o medico valida.
- confrontar(): terceiro uso do Decider. Condicional — so roda se ha historico
  anterior. Informativo — nunca bloqueia a validacao; reporta se falhar."""
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core.config import get_settings
from genrisk_agent.decider_client import DeciderClient, choice

CONFRONTO_QUESTION = "Is the current analysis consistent with the patient's prior validated history?"
CONFRONTO_OPTIONS = {
    "consistente": "current analysis agrees with the prior history",
    "evolucao_esperada": "it changed, but in an expected clinical progression",
    "conflito_com_historico": "it contradicts what was previously recorded",
}


@dataclass
class Confronto:
    ran: bool
    verdict: str = ""
    confidence: float = 0.0
    error: str = ""
    sem_historico: bool = False


def _tabela():
    s = get_settings()
    return boto3.resource("dynamodb", region_name=s.AWS_REGION).Table(s.HISTORICO_TABLE)


def listar_historico(paciente_id: str) -> list[dict]:
    try:
        resp = _tabela().query(
            KeyConditionExpression=Key("paciente_id").eq(paciente_id),
            ScanIndexForward=True,  # cronologico
        )
        return resp.get("Items", [])
    except ClientError:
        return []


def registrar(paciente_id: str, resumo: str, posicao_final: dict, ecg_verdict: str) -> bool:
    """Grava no historico (chamado SO na validacao do medico)."""
    item = {
        "paciente_id": paciente_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resumo": resumo,
        "posicao_final": json.dumps(posicao_final, ensure_ascii=False),
        "ecg_verdict": ecg_verdict,
    }
    try:
        _tabela().put_item(Item=item)
        return True
    except ClientError:
        return False


def confrontar(paciente_id: str, resumo_atual: str) -> Confronto:
    """Terceiro uso do Decider: confronta a analise atual com o historico.
    Condicional (so roda se ha historico). Informativo (nunca bloqueia)."""
    historico = listar_historico(paciente_id)
    if not historico:
        return Confronto(ran=False, sem_historico=True)

    resumos = "\n---\n".join(
        f"[{h.get('timestamp', '')}] {h.get('resumo', '')}" for h in historico
    )
    state = (f"CURRENT ANALYSIS:\n{resumo_atual}\n\n"
             f"PRIOR VALIDATED HISTORY:\n{resumos}")
    try:
        s = get_settings()
        r = DeciderClient(arn=s.DECIDER_ARN).decide(
            state, {"hist": choice(CONFRONTO_QUESTION, CONFRONTO_OPTIONS)})
        ans = r["answers"]["hist"]
        return Confronto(ran=True, verdict=ans["choice"],
                         confidence=float(ans.get("confidence", 0.0)))
    except Exception as e:
        return Confronto(ran=False, error=type(e).__name__)