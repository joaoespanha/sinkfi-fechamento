"""A rota do fechamento (ADR 0006): a rodada mais recente com o resumo calculado na leitura."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sinkfi.api import app, obter_sessao
from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.rodadas import rodar_fechamento

from tests.construtores import CORTE
from tests.integracao.cenarios import MARINA, dados_com_credito_a_mais, preparar_marina


@pytest.fixture
def cliente_http(sessao: Session) -> Iterator[TestClient]:
    app.dependency_overrides[obter_sessao] = lambda: sessao
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_resumo_usa_o_limite_atual_na_leitura(sessao: Session, cliente_http: TestClient):
    preparar_marina(sessao)
    rodar_fechamento(sessao, MARINA, CORTE)
    # O limite muda depois da rodada: o resumo tem que usar o valor de agora.
    repositorios.definir_limite(sessao, MARINA, 200000)

    resposta = cliente_http.get(f"/clientes/{MARINA}/fechamento")

    assert resposta.status_code == 200
    resumo = resposta.json()["resumo"]
    assert resumo["recomendacao"] == "nao_feche"
    assert resumo["falta_de_verdade_centavos"] == 1085933
    assert resumo["limite_trava_centavos"] == 200000


def test_limite_nulo_desliga_a_trava(sessao: Session, cliente_http: TestClient):
    preparar_marina(sessao)
    rodar_fechamento(sessao, MARINA, CORTE)

    resposta = cliente_http.get(f"/clientes/{MARINA}/fechamento")

    assert resposta.status_code == 200
    resumo = resposta.json()["resumo"]
    assert resumo["recomendacao"] == "faltam"
    assert resumo["falta_de_verdade_centavos"] == 1085933
    assert resumo["itens_falta_de_verdade"] == 5
    assert resumo["itens_para_conferir"] == 2


def test_fechamento_mostra_a_rodada_mais_recente(
    sessao: Session, cliente_http: TestClient, tmp_path: Path
):
    preparar_marina(sessao)
    rodar_fechamento(sessao, MARINA, CORTE)
    ingerir(sessao, MARINA, dados_com_credito_a_mais(tmp_path))
    nova = rodar_fechamento(sessao, MARINA, CORTE)

    resposta = cliente_http.get(f"/clientes/{MARINA}/fechamento")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["rodada"]["id"] == nova.id
    # O crédito a mais do reenvio vira um terceiro item para conferir; a rodada antiga tinha 2.
    assert corpo["resumo"]["itens_para_conferir"] == 3


def test_cliente_sem_rodada_responde_404(sessao: Session, cliente_http: TestClient):
    preparar_marina(sessao)

    resposta = cliente_http.get(f"/clientes/{MARINA}/fechamento")

    assert resposta.status_code == 404
