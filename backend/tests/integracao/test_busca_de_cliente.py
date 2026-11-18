"""O suporte acha o cliente por e-mail, CNPJ ou nome (ADR 0010)."""

from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from tests.integracao.cenarios import (
    LOJISTA_MARINA,
    LOJISTA_OUTRO,
    MARINA,
    OUTRO,
    SUPORTE,
    criar_lojista,
    criar_suporte,
    entrar,
    preparar_marina,
    preparar_outro_cliente,
)


@pytest.fixture
def suporte_com_marina(sessao: Session, http: TestClient) -> TestClient:
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    criar_suporte(sessao)
    entrar(http, SUPORTE)
    return http


def _criar_cliente(sessao: Session, id: str, nome: str) -> None:
    """Cliente sem lojista nem lojas: só o nome para achar."""
    repositorios.criar_cliente(
        sessao, id=id, nome=nome, dia_fechamento=1, hora_corte=time(18, 0), fuso="America/Sao_Paulo"
    )


def _ids(resposta) -> list[str]:
    assert resposta.status_code == 200, resposta.text
    return [cliente["id"] for cliente in resposta.json()]


def test_suporte_acha_o_cliente_pelo_email_da_lojista(suporte_com_marina: TestClient):
    resposta = suporte_com_marina.get("/clientes", params={"busca": "MARINA@sinkfi"})

    assert _ids(resposta) == [MARINA]
    assert resposta.json()[0]["nome"] == "Marina"


@pytest.mark.parametrize("termo", ["10.493.827/0001-60", "10493827000160", "493.827"])
def test_suporte_acha_o_cliente_pelo_cnpj_com_ou_sem_pontuacao(suporte_com_marina: TestClient, termo: str):
    resposta = suporte_com_marina.get("/clientes", params={"busca": termo})

    assert _ids(resposta) == [MARINA]


def test_suporte_acha_o_cliente_pelo_nome(sessao: Session, suporte_com_marina: TestClient):
    _criar_cliente(sessao, "cli_padaria", "Padaria Estrela")

    assert _ids(suporte_com_marina.get("/clientes", params={"busca": "estrela"})) == ["cli_padaria"]
    # O nome da loja também leva ao cliente.
    assert _ids(suporte_com_marina.get("/clientes", params={"busca": "savassi"})) == [MARINA]


def test_suporte_nao_aparece_na_busca(suporte_com_marina: TestClient):
    # O e-mail do suporte casa com o termo, mas ele não tem cliente: só a lojista leva à Marina.
    assert _ids(suporte_com_marina.get("/clientes", params={"busca": "sinkfi.test"})) == [MARINA]


def test_busca_devolve_so_o_cliente_que_bate(sessao: Session, suporte_com_marina: TestClient):
    preparar_outro_cliente(sessao)

    assert _ids(suporte_com_marina.get("/clientes", params={"busca": LOJISTA_OUTRO})) == [OUTRO]
    assert _ids(suporte_com_marina.get("/clientes", params={"busca": "marina"})) == [MARINA]


def test_lojas_com_o_mesmo_cnpj_dao_um_resultado_so(suporte_com_marina: TestClient):
    # As duas lojas da Marina (Centro e Savassi) têm o mesmo documento.
    resposta = suporte_com_marina.get("/clientes", params={"busca": "loja"})

    assert _ids(resposta) == [MARINA]
    assert resposta.json()[0]["lojas"] == [
        {"nome": "Loja Centro", "documento": "10493827000160"},
        {"nome": "Loja Savassi", "documento": "10493827000160"},
    ]


def test_lojista_nao_busca_clientes(sessao: Session, http: TestClient):
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    entrar(http, LOJISTA_MARINA)

    assert http.get("/clientes", params={"busca": "marina"}).status_code == 403


def test_busca_sem_token_devolve_401(http: TestClient):
    assert http.get("/clientes", params={"busca": "marina"}).status_code == 401


def test_busca_devolve_no_maximo_10_em_ordem_de_nome(sessao: Session, suporte_com_marina: TestClient):
    for n in range(11, 0, -1):
        _criar_cliente(sessao, f"cli_rede_{n:02}", f"Rede {n:02}")

    ids = _ids(suporte_com_marina.get("/clientes", params={"busca": "rede"}))

    assert ids == [f"cli_rede_{n:02}" for n in range(1, 11)]


@pytest.mark.parametrize("termo", ["", "ma", "  ma  "])
def test_termo_curto_devolve_422(suporte_com_marina: TestClient, termo: str):
    assert suporte_com_marina.get("/clientes", params={"busca": termo}).status_code == 422
