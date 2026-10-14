"""Testa o grounding gate sem chamar o Decider real.
Mocka genrisk_agent.grounding_gate._cliente — nunca toca em AWS.
"""
import genrisk_agent.grounding_gate as gate


class _FakeDecider:
    """decide() devolve P(yes) conforme um gatilho presente no state."""
    def __init__(self, mapa):
        self._mapa = mapa

    def decide(self, state, questions, **kw):
        p = 0.99
        for gatilho, valor in self._mapa.items():
            if gatilho in state:
                p = valor
                break
        chave = next(iter(questions))
        return {"answers": {chave: {"type": "noul", "noul": p}}}


def _mock(monkeypatch, mapa):
    gate._cliente.cache_clear()
    monkeypatch.setattr(gate, "_cliente", lambda: _FakeDecider(mapa))


def test_mapa_fontes_inclui_laudo_e_chunks():
    chunks = [{"id": "c1", "texto": "FTO associado a obesidade"}]
    mapa = gate.construir_mapa_fontes(chunks, laudo_contexto="laudo do paciente")
    assert mapa["c1"] == "FTO associado a obesidade"
    assert mapa["laudo"] == "laudo do paciente"


def test_afirmacao_sustentada_passa(monkeypatch):
    _mock(monkeypatch, {"FTO": 0.83})
    v = gate.auditar_cruzamento("FTO eleva risco de obesidade", ["c1"],
                                {"c1": "FTO associado a obesidade"})
    assert v.ok is True
    assert v.p_supported == 0.83


def test_afirmacao_nao_sustentada_bloqueia(monkeypatch):
    _mock(monkeypatch, {"BRCA1": 0.20})
    v = gate.auditar_cruzamento("BRCA1 eleva risco cardiometabolico", ["c1"],
                                {"c1": "FTO associado a obesidade"})
    assert v.ok is False


def test_decider_indisponivel_falha_fechada(monkeypatch):
    class _Quebrado:
        def decide(self, *a, **k):
            raise RuntimeError("runtime down")
    gate._cliente.cache_clear()
    monkeypatch.setattr(gate, "_cliente", lambda: _Quebrado())
    v = gate.auditar_cruzamento("qualquer", ["c1"], {"c1": "x"})
    assert v.ok is False
    assert v.p_supported == 0.0


def test_auditar_leitura_sumariza(monkeypatch):
    _mock(monkeypatch, {"bom": 0.90, "ruim": 0.10})
    resultado = {"cruzamentos": [
        {"afirmacao": "cruzamento bom", "fontes": ["c1"]},
        {"afirmacao": "cruzamento ruim", "fontes": ["c1"]},
    ]}
    r = gate.auditar_leitura(resultado, {"c1": "evidencia"})
    assert r["grounding_gate"]["total"] == 2
    assert r["grounding_gate"]["blocked"] == 1
    assert r["grounding_gate"]["status"] == "needs_review"