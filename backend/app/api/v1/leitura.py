"""api/v1/leitura.py — rota da leitura cruzada.

GET /api/v1/leitura/{paciente_id} -> leitura cruzada com fontes e disclaimer.
Erros controlados: paciente inexistente (404), falha de contrato/LLM (502).
"""

from fastapi import APIRouter, HTTPException

from app.core.logging_config import get_logger
from app.services.explicacao_service import gerar_leitura
from app.whatsapp_mock.fluxo_ecg import simular_ecg
from app.services.leitura_service import LaudoNaoEncontradoError, listar_pacientes

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["leitura"])

@router.get("/pacientes")
def pacientes() -> dict:
    """Lista os paciente_id canonicos disponiveis (sem o prefixo de arquivo)."""
    return {"pacientes": listar_pacientes()}


@router.get("/leitura/{paciente_id}")
def leitura(paciente_id: str) -> dict:
    try:
        return gerar_leitura(paciente_id)
    except LaudoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        logger.warning("Contract failure in reading for %s: %s", paciente_id, e)
        raise HTTPException(status_code=502, detail="Failed to generate valid reading") from e

@router.get("/consolidado/{paciente_id}")
def consolidado(paciente_id: str) -> dict:
    """Fluxo multiagente: ECG (Nova Pro + Decider) + leitura + posicao final.
    Retorna 200 com status 'pipeline_incompleto' quando um modelo nao analisou
    (nao e erro HTTP: o medico ve que faltou um modelo, nunca uma validacao)."""
    try:
        return simular_ecg(paciente_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Missing ECG data for {paciente_id}") from e
    except LaudoNaoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e