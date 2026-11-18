"""As rotas de rodadas: o histórico, a busca por NSU e a leitura de uma rodada antiga (Debugar)."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sinkfi.ingestao.ingerir import ingerir
from sinkfi.rodadas import rodar_fechamento

from tests.construtores import CORTE
from tests.integracao.cenarios import (
    LOJISTA_MARINA,
    LOJISTA_OUTRO,
    MARINA,
    OUTRO,
    SUPORTE,
    criar_lojista,
    criar_suporte,
    dados_com_credito_a_mais,
    entrar,
    preparar_marina,
    preparar_outro_cliente,
)


@pytest.fixture
def marina(sessao: Session) -> None:
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)


def test_rodada_antiga_mostra_os_itens_dela(sessao: Session, http: TestClient, marina: None, tmp_path: Path):
    antiga = rodar_fechamento(sessao, MARINA, CORTE)
    ingerir(sessao, MARINA, dados_com_credito_a_mais(tmp_path))
    nova = rodar_fechamento(sessao, MARINA, CORTE)
    entrar(http, LOJISTA_MARINA)

    resposta = http.get(f"/clientes/{MARINA}/rodadas/{antiga.id}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["rodada"]["id"] == antiga.id
    # A antiga tinha 2 itens para conferir; o crédito a mais do reenvio só está na nova.
    assert corpo["resumo"]["itens_para_conferir"] == 2
    assert http.get(f"/clientes/{MARINA}/fechamento").json()["rodada"]["id"] == nova.id


def test_rodada_de_outro_cliente_responde_404(sessao: Session, http: TestClient, marina: None):
    da_marina = rodar_fechamento(sessao, MARINA, CORTE)
    preparar_outro_cliente(sessao)
    entrar(http, LOJISTA_OUTRO)

    resposta = http.get(f"/clientes/{OUTRO}/rodadas/{da_marina.id}")

    assert resposta.status_code == 404


def test_busca_por_nsu_lista_as_rodadas_da_venda(
    sessao: Session, http: TestClient, marina: None, tmp_path: Path
):
    antiga = rodar_fechamento(sessao, MARINA, CORTE)
    ingerir(sessao, MARINA, dados_com_credito_a_mais(tmp_path))
    nova = rodar_fechamento(sessao, MARINA, CORTE)
    entrar(http, LOJISTA_MARINA)

    com_venda = http.get(f"/clientes/{MARINA}/rodadas", params={"nsu": "STN-1002"})
    sem_venda = http.get(f"/clientes/{MARINA}/rodadas", params={"nsu": "STN-NAO-EXISTE"})

    assert com_venda.status_code == 200
    assert [r["id"] for r in com_venda.json()] == [nova.id, antiga.id]
    assert sem_venda.json() == []


def test_sem_nsu_lista_todas_as_rodadas(sessao: Session, http: TestClient, marina: None):
    de_10 = rodar_fechamento(sessao, MARINA, CORTE)
    de_17 = rodar_fechamento(sessao, MARINA, datetime(2026, 11, 17, 18, 0, tzinfo=ZoneInfo("America/Sao_Paulo")))
    entrar(http, LOJISTA_MARINA)

    resposta = http.get(f"/clientes/{MARINA}/rodadas")

    assert resposta.status_code == 200
    assert [(r["id"], r["data_fechamento"]) for r in resposta.json()] == [
        (de_17.id, "2026-11-17"),
        (de_10.id, "2026-11-10"),
    ]


def test_suporte_le_a_rodada_de_qualquer_cliente(sessao: Session, http: TestClient, marina: None):
    rodada = rodar_fechamento(sessao, MARINA, CORTE)
    criar_suporte(sessao)
    entrar(http, SUPORTE)

    resposta = http.get(f"/clientes/{MARINA}/rodadas/{rodada.id}")

    assert resposta.status_code == 200
    assert resposta.json()["rodada"]["id"] == rodada.id
