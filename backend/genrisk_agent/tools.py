"""GenHealthy cross-reading exposed as a Strands tool, audited by Decider 2B."""
from __future__ import annotations
from strands import tool  # confirm path against the installed SDK version
from app.rag.store import buscar_hibrido
from app.services.explicacao_service import gerar_leitura, TERMOS_BUSCA
from app.services.leitura_service import carregar_laudo
from app.schemas.paciente import PacienteLaudo
from .grounding_gate import construir_mapa_fontes, auditar_leitura


def _laudo_para_texto(laudo: PacienteLaudo) -> str:
    linhas = [f"{d.doenca}: {d.risco_percentual}% ({d.faixa})" for d in laudo.doencas]
    linhas += [f"{f.farmaco}: {f.interpretacao}" for f in laudo.farma]
    linhas += [f"{t.caracteristica}: {t.interpretacao}" for t in laudo.fit]
    return "\n".join(linhas)


@tool
def leitura_cruzada_auditada(paciente_id: str) -> dict:
    """Generate the cross-reading (Bedrock) and audit each statement with Decider 2B."""
    resultado = gerar_leitura(paciente_id)
    chunks = buscar_hibrido(TERMOS_BUSCA, k=6)
    mapa = construir_mapa_fontes(
        chunks, laudo_contexto=_laudo_para_texto(carregar_laudo(paciente_id)))
    return auditar_leitura(resultado, mapa)