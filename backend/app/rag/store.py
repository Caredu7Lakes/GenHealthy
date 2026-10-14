"""rag/store.py — busca semantica sobre o indice FAISS.

Carrega o indice construido por ingest.py e expoe `buscar(query, k)`.
Sem LLM: retorna os chunks mais proximos da query. Coracao do teste
de aceite da Sprint 2 (busca por variante retorna o trecho certo).
"""
import re
import numpy as np
import json
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class IndiceNaoConstruidoError(Exception):
    """Disparado quando o indice FAISS ainda nao foi construido."""


@lru_cache
def _carregar():
    import faiss

    from app.rag.ingest import carregar_modelo

    settings = get_settings()
    out = Path(settings.FAISS_INDEX_PATH)
    idx_path = out / "index.faiss"
    chunks_path = out / "chunks.json"
    if not idx_path.exists() or not chunks_path.exists():
        raise IndiceNaoConstruidoError(
            f"Indice nao encontrado em {out}. Rode ingest.construir_indice() antes."
        )
    modelo = carregar_modelo()
    indice = faiss.read_index(str(idx_path))
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    return modelo, indice, chunks


def buscar(query: str, k: int = 4) -> list[dict]:
    import numpy as np

    modelo, indice, chunks = _carregar()
    vq = modelo.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    vq = np.asarray(vq, dtype="float32")
    scores, idxs = indice.search(vq, min(k, len(chunks)))
    resultados = []
    for score, i in zip(scores[0], idxs[0]):
        if i < 0:
            continue
        item = dict(chunks[i])
        item["score"] = float(score)
        resultados.append(item)
    return resultados


def _termos_chave(query: str) -> set[str]:
    """Extrai rsIDs (rs\\d+) e símbolos de gene (maiúsculas/dígitos) da query."""
    rsids = set(re.findall(r"rs\d+", query.lower()))
    genes = set(re.findall(r"\b[A-Z][A-Z0-9]{1,9}\b", query))
    return rsids | genes


def buscar_hibrido(query: str, k: int = 4, peso_lexico: float = 0.3) -> list[dict]:
    """Retrieve híbrido: score vetorial (FAISS) + reforço léxico por rsid/gene.

    O match exato de rsid/gene é o sinal defensável em genômica (identidade de
    variante não pode depender só de proximidade semântica). Fonte com termo
    citado sobe no ranking; o grounding gate recebe evidência mais precisa.
    """
    

    modelo, indice, chunks = _carregar()
    termos = _termos_chave(query)

    vq = modelo.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    vq = np.asarray(vq, dtype="float32")
    pool = min(max(k * 3, k), len(chunks))
    scores, idxs = indice.search(vq, pool)

    resultados = []
    for score, i in zip(scores[0], idxs[0]):
        if i < 0:
            continue
        item = dict(chunks[i])
        vet = float(score)
        campos = {str(item.get("rsid", "")), str(item.get("gene", ""))}
        campos |= set(re.findall(r"rs\d+", item.get("texto", "").lower()))
        hit = bool(termos & {c for c in campos if c})
        item["score_vetorial"] = vet
        item["match_lexico"] = hit
        item["score"] = (1 - peso_lexico) * vet + peso_lexico * (1.0 if hit else 0.0)
        resultados.append(item)

    resultados.sort(key=lambda r: r["score"], reverse=True)
    return resultados[:k]