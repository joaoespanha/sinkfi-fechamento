"""A saúde da operação (Monitorar): o que está parado sem o plantão saber, numa rota só do suporte."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sinkfi.api import app, obter_agora
from sinkfi.fila import obter_fila
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.outbox import publicar_pendentes

from tests.integracao.cenarios import (
    DADOS,
    LOJISTA_MARINA,
    MARINA,
    SUPORTE,
    FilaFalsa,
    criar_lojista,
    criar_suporte,
    entrar,
    preparar_marina,
)


@pytest.fixture
def fila() -> FilaFalsa:
    return FilaFalsa()


@pytest.fixture
def suporte(sessao: Session, http: TestClient, fila: FilaFalsa) -> TestClient:
    criar_suporte(sessao)
    app.dependency_overrides[obter_fila] = lambda: fila
    entrar(http, SUPORTE)
    return http


def test_operacao_conta_pedidos_parados_e_a_idade_do_mais_antigo(
    sessao: Session, suporte: TestClient, fila: FilaFalsa
):
    # Um pedido publicado e dois parados: o relay não rodou depois das duas últimas ingestões.
    preparar_marina(sessao)
    publicar_pendentes(sessao, fila)
    ingerir(sessao, MARINA, DADOS)
    ingerir(sessao, MARINA, DADOS)
    # O pedido nasce com a hora do banco; a api olha 10 minutos depois.
    gravado_em = sessao.scalar(select(func.now()))
    app.dependency_overrides[obter_agora] = lambda: gravado_em + timedelta(minutes=10)

    resposta = suporte.get("/operacao")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["pedidos_parados"] == 2
    assert corpo["idade_do_mais_antigo_segundos"] == 600


def test_operacao_mostra_mensagens_na_dead_letter(suporte: TestClient, fila: FilaFalsa):
    fila.dead_letter = 3

    corpo = suporte.get("/operacao").json()

    assert corpo["mensagens_na_dead_letter"] == 3
    # Sem pedido parado, não há idade.
    assert corpo["pedidos_parados"] == 0
    assert corpo["idade_do_mais_antigo_segundos"] is None


def test_lojista_nao_ve_operacao(sessao: Session, http: TestClient):
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    entrar(http, LOJISTA_MARINA)

    resposta = http.get("/operacao")

    assert resposta.status_code == 403
