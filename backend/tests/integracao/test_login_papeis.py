"""Login e os dois papéis (ADR 0005): quem vê o quê, e o ponto único de checagem."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sinkfi import usuarios
from sinkfi.api import app
from sinkfi.rodadas import rodar_fechamento

from tests.construtores import CORTE
from tests.integracao.cenarios import (
    LOJISTA_MARINA,
    LOJISTA_OUTRO,
    MARINA,
    SUPORTE,
    criar_lojista,
    criar_suporte,
    entrar,
    preparar_marina,
    preparar_outro_cliente,
)


def _rotas_com_cliente() -> list[tuple[str, str]]:
    """Toda rota com cliente no endereço, lida do contrato do app: rota nova entra sozinha no teste."""
    rotas = [
        (metodo.upper(), caminho)
        for caminho, operacoes in app.openapi()["paths"].items()
        if caminho.startswith("/clientes/{cliente_id}")
        for metodo in operacoes
    ]
    assert ("GET", "/clientes/{cliente_id}/fechamento") in rotas
    return sorted(rotas)


ROTAS_COM_CLIENTE = _rotas_com_cliente()


@pytest.fixture
def marina_com_rodada(sessao: Session) -> int:
    """O id da rodada, para as rotas que têm `{rodada_id}` no endereço."""
    preparar_marina(sessao)
    return rodar_fechamento(sessao, MARINA, CORTE).id


@pytest.mark.parametrize(("metodo", "caminho"), ROTAS_COM_CLIENTE)
def test_lojista_nao_ve_fechamento_de_outro_cliente(
    sessao: Session, http: TestClient, marina_com_rodada: int, metodo: str, caminho: str
):
    # A Marina tem rodada: o 404 vem do dono, não da falta de dados.
    preparar_outro_cliente(sessao)
    entrar(http, LOJISTA_OUTRO)

    resposta = http.request(metodo, caminho.format(cliente_id=MARINA, rodada_id=marina_com_rodada), json={})

    assert resposta.status_code == 404


def test_suporte_ve_qualquer_cliente(sessao: Session, http: TestClient, marina_com_rodada: int):
    criar_suporte(sessao)
    entrar(http, SUPORTE)

    resposta = http.get(f"/clientes/{MARINA}/fechamento")

    assert resposta.status_code == 200
    assert resposta.json()["resumo"]["falta_de_verdade_centavos"] == 1085933


def test_lojista_nao_reprocessa(sessao: Session, http: TestClient, marina_com_rodada: int):
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    entrar(http, LOJISTA_MARINA)

    resposta = http.post(f"/clientes/{MARINA}/reprocessar")

    assert resposta.status_code == 403


def test_suporte_nao_muda_o_limite(sessao: Session, http: TestClient, marina_com_rodada: int):
    criar_suporte(sessao)
    entrar(http, SUPORTE)

    resposta = http.put(f"/clientes/{MARINA}/limite", json={"limite_trava_centavos": 200000})

    assert resposta.status_code == 403
    resumo = http.get(f"/clientes/{MARINA}/fechamento").json()["resumo"]
    assert resumo["limite_trava_centavos"] is None


def test_suporte_le_o_limite(sessao: Session, http: TestClient, marina_com_rodada: int):
    criar_suporte(sessao)
    entrar(http, SUPORTE)

    resposta = http.get(f"/clientes/{MARINA}/limite")

    assert resposta.status_code == 200
    assert resposta.json() == {"limite_trava_centavos": None}


@pytest.mark.parametrize(("metodo", "caminho"), [*ROTAS_COM_CLIENTE, ("GET", "/eu"), ("GET", "/operacao")])
def test_rota_sem_token_devolve_401(
    http: TestClient, marina_com_rodada: int, metodo: str, caminho: str
):
    resposta = http.request(metodo, caminho.format(cliente_id=MARINA, rodada_id=marina_com_rodada), json={})

    assert resposta.status_code == 401


def test_usuario_inativo_perde_o_acesso_com_token_valido(
    sessao: Session, http: TestClient, marina_com_rodada: int
):
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    entrar(http, LOJISTA_MARINA)
    assert http.get(f"/clientes/{MARINA}/fechamento").status_code == 200

    usuarios.desativar_usuario(sessao, LOJISTA_MARINA)

    assert http.get(f"/clientes/{MARINA}/fechamento").status_code == 401


def test_senha_errada_devolve_401(sessao: Session, http: TestClient, marina_com_rodada: int):
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)

    resposta = http.post("/login", json={"email": LOJISTA_MARINA, "senha": "outra-senha"})

    assert resposta.status_code == 401
    assert http.get(f"/clientes/{MARINA}/fechamento").status_code == 401
