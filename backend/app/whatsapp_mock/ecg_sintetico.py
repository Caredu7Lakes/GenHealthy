"""Gera ECGs sintéticos para a demo (não diagnósticos).
'conforme': ritmo regular com onda P antes de cada QRS.
'nao_conforme': R-R irregular, sem onda P (padrão FA)."""
from __future__ import annotations
import io
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _beat(t: np.ndarray, com_p: bool) -> np.ndarray:
    y = np.zeros_like(t)
    if com_p:
        y += 0.15 * np.exp(-((t - 0.2) ** 2) / 0.002)      # onda P
    y += -0.1 * np.exp(-((t - 0.38) ** 2) / 0.0004)         # Q
    y += 1.0 * np.exp(-((t - 0.4) ** 2) / 0.0008)           # R
    y += -0.2 * np.exp(-((t - 0.42) ** 2) / 0.0004)         # S
    y += 0.25 * np.exp(-((t - 0.6) ** 2) / 0.003)           # T
    return y


def gerar(conforme: bool) -> bytes:
    fs = 500
    if conforme:
        rr = [0.8] * 10                                      # regular
        com_p = True
    else:
        rng = np.random.default_rng(42)
        rr = list(0.5 + rng.random(14) * 0.6)                # irregular
        com_p = False

    sinal, base = [], 0.0
    for intervalo in rr:
        t = np.linspace(0, intervalo, int(fs * intervalo))
        sinal.append(_beat(t / intervalo * 0.8, com_p))
        base += intervalo
    y = np.concatenate(sinal)
    x = np.linspace(0, base, len(y))

    fig, ax = plt.subplots(figsize=(10, 2.5))
    ax.plot(x, y, color="#111", linewidth=0.8)
    ax.set_facecolor("#fff0f0")
    ax.grid(True, color="#f3b0b0", linewidth=0.4)
    ax.set_yticks([]); ax.set_xlabel("time (s)")
    ax.set_title("ECG lead II" + ("" if conforme else " "))
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()