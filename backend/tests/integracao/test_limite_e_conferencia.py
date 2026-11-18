"""Limite da trava e conferência (#12): cada mudança e cada conferência ficam registrados, e nada disso cria rodada."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.rodadas import rodar_fechamento
from sinkfi.tipos import Rodada

from tests.construtores import CORTE
from tests.integracao.cenarios import (
    LOJISTA_MARINA,
    MARINA,
    SUPORTE,
    criar_lojista,
    criar_suporte,
    dados_com_credito_a_mais,
    entrar,
    preparar_marina,
)


@pytest.fixture
def rodada(sessao: Session) -> Rodada:
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    return rodar_fechamento(sessao, MARINA, CORTE)


@pytest.fixture
def lojista(http: TestClient, rodada: Rodada) -> TestClient:
    entrar(http, LOJISTA_MARINA)
    return http


def _rodada_nova(sessao: Session, pasta: Path) -> Rodada:
    """O lote reenviado com um crédito a mais: a rodada nova tem 3 itens para conferir, a antiga 2."""
    ingerir(sessao, MARINA, dados_com_credito_a_mais(pasta))
    return rodar_fechamento(sessao, MARINA, CORTE)


def _agora(momento: str | datetime) -> bool:
    if isinstance(momento, str):
        momento = datetime.fromisoformat(momento)
    return abs(datetime.now(UTC) - momento) < timedelta(minutes=1)


def _mudar_limite(http: TestClient, centavos: int | None) -> None:
    resposta = http.put(f"/clientes/{MARINA}/limite", json={"limite_trava_centavos": centavos})
    assert resposta.status_code == 204, resposta.text


def _conferir(http: TestClient, rodada_id: int) -> dict:
    resposta = http.post(f"/clientes/{MARINA}/conferencias", json={"rodada_id": rodada_id})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# Limite


def test_mudar_limite_nao_cria_rodada_nova(sessao: Session, lojista: TestClient, rodada: Rodada):
    _mudar_limite(lojista, 200000)

    assert [r.id for r in repositorios.rodadas_do_cliente(sessao, MARINA)] == [rodada.id]
    corpo = lojista.get(f"/clientes/{MARINA}/fechamento").json()
    assert corpo["rodada"]["id"] == rodada.id
    assert corpo["resumo"]["recomendacao"] == "nao_feche"


def test_mudanca_de_limite_fica_registrada(sessao: Session, lojista: TestClient):
    _mudar_limite(lojista, 200000)
    _mudar_limite(lojista, None)

    mudancas = repositorios.mudancas_de_limite(sessao, MARINA)

    # Da mais antiga para a mais nova. None = trava desligada.
    assert [(m.quem, m.de_centavos, m.para_centavos) for m in mudancas] == [
        (LOJISTA_MARINA, None, 200000),
        (LOJISTA_MARINA, 200000, None),
    ]
    assert all(_agora(m.em) for m in mudancas)


def test_le_o_limite_atual(lojista: TestClient):
    _mudar_limite(lojista, 200000)
    assert lojista.get(f"/clientes/{MARINA}/limite").json() == {"limite_trava_centavos": 200000}

    _mudar_limite(lojista, None)
    assert lojista.get(f"/clientes/{MARINA}/limite").json() == {"limite_trava_centavos": None}


def test_le_o_limite_sem_fechamento(sessao: Session, http: TestClient):
    # A tela de Limite (#25) não depende de haver rodada.
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    entrar(http, LOJISTA_MARINA)

    resposta = http.get(f"/clientes/{MARINA}/limite")

    assert resposta.status_code == 200
    assert resposta.json() == {"limite_trava_centavos": None}


# Término


def test_conferencia_grava_quem_quando_e_a_rodada_vista(lojista: TestClient, rodada: Rodada):
    conferencia = _conferir(lojista, rodada.id)

    assert conferencia["quem"] == LOJISTA_MARINA
    assert conferencia["rodada_id"] == rodada.id
    assert _agora(conferencia["em"])
    assert lojista.get(f"/clientes/{MARINA}/fechamento").json()["ultima_conferencia"] == conferencia


def test_conferencia_nao_bloqueia_rodada_nova(
    sessao: Session, lojista: TestClient, rodada: Rodada, tmp_path: Path
):
    _conferir(lojista, rodada.id)

    nova = _rodada_nova(sessao, tmp_path)

    assert nova.id != rodada.id
    assert lojista.get(f"/clientes/{MARINA}/fechamento").json()["rodada"]["id"] == nova.id


def test_rodada_nova_depois_da_conferencia_mostra_o_que_mudou(
    sessao: Session, lojista: TestClient, rodada: Rodada, tmp_path: Path
):
    _conferir(lojista, rodada.id)
    nova = _rodada_nova(sessao, tmp_path)

    corpo = lojista.get(f"/clientes/{MARINA}/fechamento").json()

    # A tela compara as duas rodadas e mostra o resumo de antes e o de agora.
    assert corpo["rodada"]["id"] == nova.id
    assert corpo["ultima_conferencia"]["rodada_id"] == rodada.id
    assert corpo["ultima_conferencia"]["resumo"]["itens_para_conferir"] == 2
    assert corpo["resumo"]["itens_para_conferir"] == 3


def test_conferencia_de_novo_guarda_os_dois_registros(
    sessao: Session, lojista: TestClient, rodada: Rodada
):
    primeiro = _conferir(lojista, rodada.id)
    _mudar_limite(lojista, 200000)
    segundo = _conferir(lojista, rodada.id)

    conferencias = repositorios.conferencias_do_cliente(sessao, MARINA)

    # Do mais antigo para o mais novo; o segundo não sobrescreve o primeiro.
    assert [t.limite_trava_centavos for t in conferencias] == [None, 200000]
    assert primeiro != segundo
    assert lojista.get(f"/clientes/{MARINA}/fechamento").json()["ultima_conferencia"] == segundo


def test_conferencia_guarda_limite_e_resumo_do_momento(lojista: TestClient, rodada: Rodada):
    _mudar_limite(lojista, 200000)
    _conferir(lojista, rodada.id)

    # O limite muda depois do término: o registro continua com o de antes.
    _mudar_limite(lojista, None)
    corpo = lojista.get(f"/clientes/{MARINA}/fechamento").json()

    conferencia = corpo["ultima_conferencia"]
    assert conferencia["limite_trava_centavos"] == 200000
    assert conferencia["resumo"] == {
        "recomendacao": "nao_feche",
        "falta_de_verdade_centavos": 1085933,
        "itens_falta_de_verdade": 5,
        "itens_para_conferir": 2,
        "limite_trava_centavos": 200000,
    }
    assert corpo["resumo"]["recomendacao"] == "faltam"


# Extras aprovados junto com as decisões do #12


def test_suporte_nao_marca_conferido(sessao: Session, http: TestClient, rodada: Rodada):
    criar_suporte(sessao)
    entrar(http, SUPORTE)

    resposta = http.post(f"/clientes/{MARINA}/conferencias", json={"rodada_id": rodada.id})

    assert resposta.status_code == 403
    assert repositorios.conferencias_do_cliente(sessao, MARINA) == []


def test_conferencia_com_rodada_que_nao_e_do_cliente_devolve_404(sessao: Session, lojista: TestClient):
    resposta = lojista.post(f"/clientes/{MARINA}/conferencias", json={"rodada_id": 999_999})

    assert resposta.status_code == 404
    assert repositorios.conferencias_do_cliente(sessao, MARINA) == []


def test_fechamento_sem_conferencia_vem_com_ultima_conferencia_nula(lojista: TestClient):
    corpo = lojista.get(f"/clientes/{MARINA}/fechamento").json()

    assert corpo["ultima_conferencia"] is None
