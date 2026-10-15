"""Fluxo multiagente ECG com trava de integridade.

Pre-condicao: a posicao final so e produzida se Nova Pro (visao) E Claude
(leitura) participaram. Se qualquer um nao analisou (ex. cota), o pipeline
retorna pipeline_incompleto informando qual modelo faltou."""
from __future__ import annotations
import json
from pathlib import Path
import base64

from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.services.explicacao_service import gerar_leitura, TERMOS_BUSCA
from app.rag.store import buscar_hibrido
from genrisk_agent.grounding_gate import construir_mapa_fontes, auditar_leitura
from genrisk_agent.decider_client import DeciderClient, choice
from .envelope import lacrar
from .vision_client import analisar_ecg
from .consolidacao import consolidar
from .historico import confrontar

SENHA = "sete-lagos-2026"
ECG_QUESTION = "Is the ECG report consistent with what the ECG image shows?"
ECG_OPTIONS = {
    "conforme": "report and image agree",
    "nao_conforme": "report contradicts the image",
    "inconclusivo": "the image does not support a conclusion",
}


def _ecg_dir() -> Path:
    return Path(get_settings().LAUDOS_DIR).parent / "ecg"


def _incompleto(modelo: str, motivo: str, log: list[str]) -> dict:
    log.append(f"[PIPELINE INCOMPLETO] {modelo} nao analisou: {motivo}")
    return {
        "log": log,
        "status": "pipeline_incompleto",
        "modelo_faltante": modelo,
        "motivo": motivo,
        "posicao_final": None,
    }


def simular_ecg(paciente_id: str) -> dict:
    s = get_settings()
    base = _ecg_dir()
    log: list[str] = []

    laudo_ecg = json.loads((base / f"{paciente_id}_laudo.json").read_text(encoding="utf-8"))
    imagem = (base / f"{paciente_id}_ecg.png").read_bytes()
    lacrar(laudo_ecg, senha=SENHA).abrir(senha=SENHA)
    log.append("[paciente->medico] ECG report + image sent (sealed).")

    vis = analisar_ecg(imagem)
    if not vis.ran:
        return _incompleto("Nova Pro (vision)", vis.error, log)
    log.append("[agent 1 - Nova Pro] image findings extracted.")

    state = (f"ECG REPORT (text):\n{laudo_ecg.get('conclusao', '')}\n\n"
             f"ECG IMAGE FINDINGS (vision):\n{vis.findings}")
    r = DeciderClient(arn=s.DECIDER_ARN).decide(state, {"ecg": choice(ECG_QUESTION, ECG_OPTIONS)})
    ans = r["answers"]["ecg"]
    ecg_verdict = ans["choice"]
    ecg_conf = float(ans.get("confidence", 0.0))
    log.append(f"[agent 2 - Decider] ECG verdict: {ecg_verdict} (conf={ecg_conf:.2f}).")

    try:
        leitura = gerar_leitura(paciente_id)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        return _incompleto("Claude (generative reading)", code, log)
    chunks = buscar_hibrido(TERMOS_BUSCA, k=6)
    leitura = auditar_leitura(leitura, construir_mapa_fontes(chunks))
    grounding_status = leitura["grounding_gate"]["status"]
    log.append(f"[grounding gate] {grounding_status}.")

    pos = consolidar(grounding_status, ecg_verdict)
    conf = confrontar(paciente_id, leitura.get("resumo", ""))
    if conf.sem_historico:
        log.append("[historico] primeiro atendimento — sem confronto.")
    elif conf.ran:
        log.append(f"[historico · Decider] confronto: {conf.verdict} (conf={conf.confidence:.2f}).")
    else:
        log.append(f"[historico] confronto indisponivel: {conf.error}.")
    log.append(f"[final position] {pos.status}: {pos.motivo}")
    log.append("[medico] awaiting validation -> send to patient.")

    return {
        "log": log,
        "status": "ok",
        "ecg": {
            "verdict": ecg_verdict,
            "confidence": round(ecg_conf, 3),
            "findings": vis.findings,
            "conclusao": laudo_ecg.get("conclusao", ""),
            "imagem_b64": base64.b64encode(imagem).decode(),
        },
        "confronto": {
            "ran": conf.ran,
            "sem_historico": conf.sem_historico,
            "verdict": conf.verdict,
            "confidence": round(conf.confidence, 3),
            "error": conf.error,
        },
        "grounding_status": grounding_status,
        "posicao_final": {"status": pos.status, "rotulo": pos.rotulo, "motivo": pos.motivo},
        "leitura": leitura,
    }



if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "ficticio_DB_0001"
    out = simular_ecg(pid)
    for l in out["log"]:
        print(l)
    print("\npipeline status:", out["status"])
    if out["status"] == "ok":
        print("ECG:", out["ecg"]["verdict"], "| final:", out["posicao_final"]["status"])
    else:
        print("missing model:", out["modelo_faltante"])
