"""Simulacao do fluxo clinico via WhatsApp (mock).

Paciente envia exames (lacrados) -> medico abre -> medico envia anamnese com
senha -> paciente abre e responde -> medico roda o GenHealthy (leitura auditada
com grounding gate) -> medico valida ou rejeita.

Reusa dados ficticios de data/ e a leitura auditada real (Bedrock + Decider).
"""
from __future__ import annotations
import json
from pathlib import Path

from app.core.config import get_settings
from app.services.explicacao_service import gerar_leitura, TERMOS_BUSCA
from app.rag.store import buscar_hibrido
from genrisk_agent.grounding_gate import construir_mapa_fontes, auditar_leitura
from .envelope import lacrar

SENHA_ANAMNESE = "sete-lagos-2026"


def _carregar_json(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def simular(paciente_id: str) -> dict:
    s = get_settings()
    log: list[str] = []

    exame_path = Path(s.EXAMES_DIR) / f"{paciente_id}_clinico.json"
    exame = _carregar_json(exame_path) if exame_path.exists() else {}
    env_exame = lacrar(exame, senha=paciente_id)
    log.append(f"[paciente->medico] Exames enviados (encrypted={env_exame.encrypted}).")

    env_exame.abrir(senha=paciente_id)
    log.append("[medico] Exames abertos com sucesso.")

    log.append("[medico->paciente] Anamnese enviada, protegida por senha.")

    anamnese = _carregar_json(Path(s.ANAMNESE_DIR) / f"{paciente_id}.json")
    env_anamnese = lacrar(anamnese, senha=SENHA_ANAMNESE)
    respondida = env_anamnese.abrir(senha=SENHA_ANAMNESE)
    log.append(f"[paciente] Anamnese aberta com a senha e respondida "
               f"({len(respondida)} campos).")

    log.append("[medico] Disparando o GenHealthy...")
    resultado = gerar_leitura(paciente_id)
    chunks = buscar_hibrido(TERMOS_BUSCA, k=6)
    mapa = construir_mapa_fontes(chunks, laudo_contexto="")
    resultado = auditar_leitura(resultado, mapa)
    gate = resultado["grounding_gate"]
    log.append(f"[grounding gate] status={gate['status']} "
               f"({gate['blocked']} de {gate['total']} retidos).")

    log.append("[medico] Aguardando validacao (validar/rejeitar).")

    return {"log": log, "leitura": resultado}


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "ficticio_DB_0001"
    out = simular(pid)
    for linha in out["log"]:
        print(linha)
    print("\nstatus:", out["leitura"]["grounding_gate"]["status"])
