"""Grounding gate por afirmação via Strands Decider 2B (#strands-decider-2b, #guardrails).

Pergunta noul (sim/não calibrado): a afirmação está sustentada pelos trechos citados?
Bloqueia quando P(yes) < GROUNDING_THRESHOLD. Falha fechada se o Decider cair.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import get_settings
from .decider_client import DeciderClient, noul

QUESTION = "Is this clinical statement supported by the cited source excerpts?"


@dataclass
class Verdict:
    afirmacao: str
    p_supported: float
    ok: bool


@lru_cache
def _cliente() -> DeciderClient:
    return DeciderClient(arn=get_settings().DECIDER_ARN)


def construir_mapa_fontes(chunks: list[dict], laudo_contexto: str = "") -> dict:
    mapa = {str(c["id"]): c.get("texto", "") for c in chunks if c.get("id") is not None}
    if laudo_contexto:
        mapa["laudo"] = laudo_contexto
    return mapa


def auditar_cruzamento(afirmacao: str, fontes: list[str], mapa: dict,
                       threshold: float | None = None) -> Verdict:
    threshold = get_settings().GROUNDING_THRESHOLD if threshold is None else threshold
    trechos = [mapa.get(str(f), "") for f in fontes]
    state = ("STATEMENT:\n" + afirmacao + "\n\nCITED SOURCES:\n"
             + "\n---\n".join(t for t in trechos if t))
    try:
        r = _cliente().decide(state, {"supported": noul(QUESTION)})
        p = float(r["answers"]["supported"]["noul"])
    except Exception:
        return Verdict(afirmacao, 0.0, ok=False)  # falha fechada
    return Verdict(afirmacao, round(p, 4), ok=p >= threshold)


def auditar_leitura(resultado: dict, mapa: dict, threshold: float | None = None) -> dict:
    veredictos = []
    for c in resultado.get("cruzamentos", []):
        v = auditar_cruzamento(c.get("afirmacao", ""), c.get("fontes", []), mapa, threshold)
        c["grounding"] = {"p_supported": v.p_supported, "ok": v.ok}
        veredictos.append(v)
    bloqueados = [v for v in veredictos if not v.ok]
    resultado["grounding_gate"] = {
        "total": len(veredictos), "blocked": len(bloqueados),
        "status": "ok" if not bloqueados else "needs_review",
    }
    return resultado