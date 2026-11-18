"""A saúde da aplicação: a api fala com o Postgres e com o broker? Sem login, para o health check do compose."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sinkfi.api import app, obter_sessao
from sinkfi.fila import obter_fila

from tests.integracao.cenarios import FilaFalsa


@pytest.fixture
def fila() -> FilaFalsa:
    fila = FilaFalsa()
    app.dependency_overrides[obter_fila] = lambda: fila
    return fila


def test_health_responde_ok_com_banco_e_broker_no_ar(http: TestClient, fila: FilaFalsa):
    # Sem `entrar`: a sonda do compose não tem login.
    resposta = http.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "postgres": "ok", "broker": "ok"}


def test_health_responde_503_e_nomeia_o_broker_quando_ele_cai(http: TestClient, fila: FilaFalsa):
    fila.broker_no_ar = False

    resposta = http.get("/health")

    # Diz o que caiu e nada mais: sem versão, host nem a mensagem do erro.
    assert resposta.status_code == 503
    assert resposta.json() == {"status": "falhou", "postgres": "ok", "broker": "falhou"}


@pytest.fixture
def banco_fora() -> Iterator[None]:
    # Uma porta sem Postgres: a conexão é recusada de verdade, como com o container parado.
    engine = create_engine("postgresql+psycopg://sinkfi:sinkfi@127.0.0.1:1/sinkfi", connect_args={"connect_timeout": 2})
    with Session(engine) as sessao:
        app.dependency_overrides[obter_sessao] = lambda: sessao
        yield
    engine.dispose()


def test_health_responde_503_quando_o_banco_cai(http: TestClient, fila: FilaFalsa, banco_fora: None):
    resposta = http.get("/health")

    assert resposta.status_code == 503
    assert resposta.json() == {"status": "falhou", "postgres": "falhou", "broker": "ok"}
