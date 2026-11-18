"""A saúde da operação (Monitorar): o que está parado sem o plantão saber, numa rota só do suporte."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from sinkfi.api import app
from sinkfi.banco.modelos import LinhaCliente, LinhaPedidoFechamento
from sinkfi.fila import obter_fila
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.outbox import publicar_pendentes

from tests.integracao.cenarios import (
    DADOS,
    LOJISTA_MARINA,
    MARINA,
    OUTRO,
    SUPORTE,
    FilaFalsa,
    criar_lojista,
    criar_suporte,
    entrar,
    preparar_marina,
    preparar_outro_cliente,
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


# O `agora` da api nos testes (conftest): 17/11 às 21:00 de São Paulo.
AGORA = datetime(2026, 11, 17, 21, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))


def _ultima_ingestao(sessao: Session, cliente_id: str, em: datetime) -> None:
    sessao.execute(update(LinhaCliente).where(LinhaCliente.id == cliente_id).values(ultima_ingestao_em=em))


def test_operacao_lista_cliente_com_ingestao_ha_mais_de_doze_horas(sessao: Session, suporte: TestClient):
    # O beat parou: a Marina não tem ingestão há 12h01, dois ciclos perdidos (ADR 0011).
    preparar_marina(sessao)
    _ultima_ingestao(sessao, MARINA, AGORA - timedelta(hours=12, minutes=1))

    corpo = suporte.get("/operacao").json()

    assert corpo["clientes_com_ingestao_atrasada"] == [MARINA]


def test_operacao_nao_lista_cliente_com_ingestao_ha_doze_horas(sessao: Session, suporte: TestClient):
    # Exatamente 12h: a mesma fronteira da linha de atualização, que só fica atrasada depois.
    preparar_marina(sessao)
    _ultima_ingestao(sessao, MARINA, AGORA - timedelta(hours=12))

    corpo = suporte.get("/operacao").json()

    assert corpo["clientes_com_ingestao_atrasada"] == []


def test_operacao_nao_lista_cliente_sem_ingestao(sessao: Session, suporte: TestClient):
    # Sem data de criação do cliente, não dá para saber se ele está atrasado ou só chegou agora.
    preparar_outro_cliente(sessao)

    corpo = suporte.get("/operacao").json()

    assert corpo["clientes_com_ingestao_atrasada"] == []


def test_operacao_devolve_a_ingestao_mais_recente_de_todos(sessao: Session, suporte: TestClient):
    # O pulso do beat: um cliente atrasado é problema dele; todos parados ao mesmo tempo é o beat.
    preparar_marina(sessao)
    preparar_outro_cliente(sessao)
    mais_recente = AGORA - timedelta(hours=2)
    _ultima_ingestao(sessao, MARINA, AGORA - timedelta(hours=13))
    _ultima_ingestao(sessao, OUTRO, mais_recente)

    corpo = suporte.get("/operacao").json()

    assert datetime.fromisoformat(corpo["ultima_ingestao_em"]) == mais_recente
