"""A saúde da operação (Monitorar): o que está parado sem o plantão saber, numa rota só do suporte."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from sinkfi.api import app
from sinkfi.banco.modelos import LinhaPedidoFechamento
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


def test_operacao_conta_pedidos_pendentes_e_a_idade_do_mais_antigo(
    sessao: Session, suporte: TestClient, fila: FilaFalsa
):
    # Um pedido publicado e dois pendentes: o relay não rodou depois das duas últimas ingestões.
    preparar_marina(sessao)
    publicar_pendentes(sessao, fila)
    ingerir(sessao, MARINA, DADOS)
    ingerir(sessao, MARINA, DADOS)
    # A idade sai só do relógio do banco: o pedido nasceu 10 minutos antes do `now()` desta transação.
    sessao.execute(
        update(LinhaPedidoFechamento)
        .where(LinhaPedidoFechamento.publicado_em.is_(None))
        .values(criado_em=func.now() - timedelta(minutes=10))
    )

    resposta = suporte.get("/operacao")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["pedidos_pendentes"] == 2
    assert corpo["idade_do_mais_antigo_segundos"] == 600


def test_operacao_mostra_mensagens_na_dead_letter(suporte: TestClient, fila: FilaFalsa):
    fila.dead_letter = 3

    corpo = suporte.get("/operacao").json()

    assert corpo["mensagens_na_dead_letter"] == 3
    # Sem pedido pendente, não há idade.
    assert corpo["pedidos_pendentes"] == 0
    assert corpo["idade_do_mais_antigo_segundos"] is None


def test_operacao_com_o_rabbitmq_fora_mostra_dead_letter_nula(suporte: TestClient, fila: FilaFalsa):
    fila.dead_letter = None

    resposta = suporte.get("/operacao")

    # A rota não cai: o resto da saúde continua visível, e `null` diz que a fila não respondeu.
    assert resposta.status_code == 200
    assert resposta.json()["mensagens_na_dead_letter"] is None


def test_lojista_nao_ve_operacao(sessao: Session, http: TestClient):
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    entrar(http, LOJISTA_MARINA)

    resposta = http.get("/operacao")

    assert resposta.status_code == 403
