"""O segredo que assina a sessão (ADR 0005): a api não sobe com um segredo que qualquer um conhece.

O padrão do `compose.yaml` está no repositório. Com ele, quem leu o código assina um token para qualquer
usuário. Ele só vale com a demonstração ligada de propósito (`SINKFI_DEMONSTRACAO=1`).
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sinkfi.api import app
from sinkfi.api.autenticacao import SEGREDO_DA_DEMONSTRACAO

COMPOSE = Path(__file__).resolve().parents[2] / "compose.yaml"
SEGREDO_PROPRIO = "um-segredo-de-verdade-com-mais-de-32-bytes"


def _subir() -> None:
    """Sobe e derruba a api: o `with` roda o lifespan, onde a checagem acontece."""
    with TestClient(app):
        pass


@pytest.fixture(autouse=True)
def _sem_demonstracao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SINKFI_DEMONSTRACAO", raising=False)


def test_api_nao_sobe_com_o_segredo_da_demonstracao_fora_dela(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET", SEGREDO_DA_DEMONSTRACAO)

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _subir()


def test_api_sobe_com_o_segredo_da_demonstracao_quando_ela_esta_ligada(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET", SEGREDO_DA_DEMONSTRACAO)
    monkeypatch.setenv("SINKFI_DEMONSTRACAO", "1")

    _subir()


def test_api_nao_sobe_sem_segredo(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _subir()


def test_api_nao_sobe_com_segredo_curto_nem_na_demonstracao(monkeypatch: pytest.MonkeyPatch):
    # HS256 pede uma chave de pelo menos 32 bytes (RFC 7518, seção 3.2).
    monkeypatch.setenv("JWT_SECRET", "x" * 31)
    monkeypatch.setenv("SINKFI_DEMONSTRACAO", "1")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _subir()


def test_api_sobe_com_segredo_proprio(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JWT_SECRET", SEGREDO_PROPRIO)

    _subir()


def test_o_padrao_do_compose_e_o_segredo_da_demonstracao():
    # Se alguém trocar o padrão no compose sem trocar aqui, a api voltaria a aceitar um segredo público.
    padrao = re.search(r"JWT_SECRET: \$\{JWT_SECRET:-(.+)\}", COMPOSE.read_text(encoding="utf-8"))

    assert padrao is not None
    assert padrao.group(1) == SEGREDO_DA_DEMONSTRACAO


def test_compose_liga_a_demonstracao_na_api():
    texto = COMPOSE.read_text(encoding="utf-8")

    assert re.search(r'SINKFI_DEMONSTRACAO: "1"', texto)
