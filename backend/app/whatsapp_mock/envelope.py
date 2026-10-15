"""Envelope simbolico de "criptografia" e "senha" para a simulacao WhatsApp.
NAO e criptografia real - apenas encena o fluxo de confidencialidade na demo.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Any


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()[:12]


@dataclass
class Envelope:
    conteudo: dict[str, Any]
    encrypted: bool
    password_hash: str

    def abrir(self, senha: str) -> dict[str, Any]:
        if not self.encrypted:
            return self.conteudo
        if _hash(senha) != self.password_hash:
            raise PermissionError("Senha incorreta - envelope permanece lacrado.")
        return self.conteudo


def lacrar(conteudo: dict[str, Any], senha: str) -> Envelope:
    return Envelope(conteudo=conteudo, encrypted=True, password_hash=_hash(senha))
