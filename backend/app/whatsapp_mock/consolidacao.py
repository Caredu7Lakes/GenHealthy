"""Consolidação determinística: funde o grounding da leitura clínica com o
referendo de conformidade do ECG numa posição final única. Sem LLM aqui —
regra explícita e auditável."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class PosicaoFinal:
    status: str          # "consistente" | "revisar" | "conflito"
    rotulo: str
    motivo: str


def consolidar(grounding_status: str, ecg_verdict: str) -> PosicaoFinal:
    if grounding_status == "needs_review":
        return PosicaoFinal("revisar", "⚠️ Hold for review",
                            "Clinical reading has statements that are not grounded.")
    if ecg_verdict == "nao_conforme":
        return PosicaoFinal("conflito", "🚫 Conflict",
                            "ECG report contradicts its own image.")
    if ecg_verdict == "inconclusivo":
        return PosicaoFinal("revisar", "⚠️ Hold for review",
                            "ECG image did not support a conclusion.")
    return PosicaoFinal("consistente", "✅ Consistent",
                        "Clinical reading grounded and ECG report matches the image.")