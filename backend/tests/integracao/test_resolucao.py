"""Resolução da pendência para conferir (ADR 0014): presa ao lançamento e ao valor, lida na hora, sem tocar na rodada."""

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
    LOJISTA_OUTRO,
    MARINA,
    OUTRO,
    SUPORTE,
    _copiar_dados,
    criar_lojista,
    criar_suporte,
    dados_com_credito_a_mais,
    entrar,
    preparar_marina,
    preparar_outro_cliente,
)

# Os dados da Marina no corte de 10/11: duas entradas sem recebível e uma venda cancelada.
APORTE = "ext_20"  # Entrada sem recebível, R$ 1.477,50.
OUTRA_ENTRADA = "ext_19"  # Entrada sem recebível, R$ 44,33.
VENDA_CANCELADA = "ext_07"  # Falta de verdade, de lançamento.


@pytest.fixture
def rodada(sessao: Session) -> Rodada:
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    return rodar_fechamento(sessao, MARINA, CORTE)


@pytest.fixture
def lojista(http: TestClient, rodada: Rodada) -> TestClient:
    entrar(http, LOJISTA_MARINA)
    return http


def _dados_com_chargeback_no_aporte(pasta: Path) -> Path:
    """O lote reenviado: os mesmos CSVs, com um chargeback de R$ 477,50 no aporte. O que fica dele é R$ 1.000,00."""
    _copiar_dados(pasta)
    with (pasta / "extrato.csv").open("a", encoding="utf-8") as extrato:
        extrato.write(
            "ext_97,T-XREFR,T-XREF,2026-11-10T12:00:00-03:00,47750,COMERCIAL ATLAS,"
            "11111111000111,DEVOLUCAO PIX,confirmed,chargeback\n"
        )
    return pasta


def _resolver(http: TestClient, rodada_id: int, lancamento_id: str, nota: str = "aporte do sócio"):
    return http.post(
        f"/clientes/{MARINA}/resolucoes",
        json={"rodada_id": rodada_id, "lancamento_id": lancamento_id, "nota": nota},
    )


def _fechamento(http: TestClient, semana: str | None = None) -> dict:
    resposta = http.get(f"/clientes/{MARINA}/fechamento", params={"semana": semana} if semana else None)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _item(corpo: dict, lancamento_id: str) -> dict:
    return next(i for i in corpo["itens"] if not i["recebiveis"] and i["creditos"][0]["id"] == lancamento_id)


def test_resolver_tira_a_pendencia_do_resumo_sem_tocar_na_rodada(
    sessao: Session, lojista: TestClient, rodada: Rodada
):
    antes = repositorios.itens_da_rodada(sessao, rodada.id)

    resposta = _resolver(lojista, rodada.id, APORTE)

    assert resposta.status_code == 201, resposta.text
    corpo = _fechamento(lojista)
    assert corpo["rodada"]["id"] == rodada.id
    assert corpo["resumo"]["itens_para_conferir"] == 1
    assert corpo["resumo"]["itens_falta_de_verdade"] == 5
    assert corpo["resumo"]["falta_de_verdade_centavos"] == 1085933
    item = _item(corpo, APORTE)
    # A pendência continua com a severidade e o motivo, e leva a marca de resolvida.
    assert item["severidade"] == "para_conferir"
    assert item["motivo"] == "entrada_sem_recebivel"
    assert item["resolucao"]["quem"] == LOJISTA_MARINA
    assert item["resolucao"]["nota"] == "aporte do sócio"
    assert abs(datetime.now(UTC) - datetime.fromisoformat(item["resolucao"]["em"])) < timedelta(minutes=1)
    assert _item(corpo, OUTRA_ENTRADA)["resolucao"] is None
    assert repositorios.itens_da_rodada(sessao, rodada.id) == antes


def test_resolucao_sobrevive_a_rodada_nova(sessao: Session, lojista: TestClient, rodada: Rodada, tmp_path: Path):
    _resolver(lojista, rodada.id, APORTE)

    # O lote reenviado traz uma entrada sem recebível a mais: a rodada nova tem 3 para conferir.
    ingerir(sessao, MARINA, dados_com_credito_a_mais(tmp_path))
    nova = rodar_fechamento(sessao, MARINA, CORTE)

    corpo = _fechamento(lojista)
    assert corpo["rodada"]["id"] == nova.id != rodada.id
    assert corpo["resumo"]["itens_para_conferir"] == 2
    assert _item(corpo, APORTE)["resolucao"]["nota"] == "aporte do sócio"


def test_resolucao_vale_nos_outros_fechamentos(sessao: Session, lojista: TestClient, rodada: Rodada):
    seguinte = rodar_fechamento(sessao, MARINA, CORTE + timedelta(days=7))
    semana = seguinte.data_fechamento.isoformat()
    assert _item(_fechamento(lojista, semana), APORTE)["resolucao"] is None

    # Resolvida no fechamento de 10/11, sai também do de 17/11.
    _resolver(lojista, rodada.id, APORTE)

    corpo = _fechamento(lojista, semana)
    assert _item(corpo, APORTE)["resolucao"]["nota"] == "aporte do sócio"
    assert corpo["resumo"]["itens_para_conferir"] == 1


def test_valor_diferente_devolve_a_pendencia(sessao: Session, lojista: TestClient, rodada: Rodada, tmp_path: Path):
    _resolver(lojista, rodada.id, APORTE)

    ingerir(sessao, MARINA, _dados_com_chargeback_no_aporte(tmp_path))
    rodar_fechamento(sessao, MARINA, CORTE)

    corpo = _fechamento(lojista)
    item = _item(corpo, APORTE)
    assert item["pendencia_centavos"] == 100000
    assert item["resolucao"] is None
    assert corpo["resumo"]["itens_para_conferir"] == 2


def test_desfazer_devolve_a_pendencia(lojista: TestClient, rodada: Rodada):
    _resolver(lojista, rodada.id, APORTE)

    resposta = lojista.delete(f"/clientes/{MARINA}/resolucoes/{APORTE}")

    assert resposta.status_code == 204, resposta.text
    corpo = _fechamento(lojista)
    assert _item(corpo, APORTE)["resolucao"] is None
    assert corpo["resumo"]["itens_para_conferir"] == 2
    # Desfeita, pode ser resolvida de novo, com outra nota.
    assert _resolver(lojista, rodada.id, APORTE, nota="Pix do cliente Atlas").status_code == 201
    assert _item(_fechamento(lojista), APORTE)["resolucao"]["nota"] == "Pix do cliente Atlas"


def test_desfazer_sem_resolucao_devolve_404(lojista: TestClient, rodada: Rodada):
    resposta = lojista.delete(f"/clientes/{MARINA}/resolucoes/{APORTE}")

    assert resposta.status_code == 404


def test_falta_de_verdade_nao_se_resolve(lojista: TestClient, rodada: Rodada):
    resposta = _resolver(lojista, rodada.id, VENDA_CANCELADA)

    assert resposta.status_code == 422
    assert _fechamento(lojista)["resumo"]["itens_falta_de_verdade"] == 5


@pytest.mark.parametrize("nota", ["", "   ", "x" * 201])
def test_nota_vazia_ou_longa_e_recusada(lojista: TestClient, rodada: Rodada, nota: str):
    resposta = _resolver(lojista, rodada.id, APORTE, nota=nota)

    assert resposta.status_code == 422
    assert _item(_fechamento(lojista), APORTE)["resolucao"] is None


def test_lancamento_fora_da_rodada_devolve_404(lojista: TestClient, rodada: Rodada):
    # ext_01 casou com um recebível: não é um item de pendência da rodada.
    assert _resolver(lojista, rodada.id, "ext_01").status_code == 404
    assert _resolver(lojista, rodada.id, "nao_existe").status_code == 404


def test_rodada_de_outro_cliente_no_corpo_devolve_404(sessao: Session, http: TestClient, rodada: Rodada):
    # A lojista do outro cliente usa a própria rota, com a rodada e o lançamento da Marina no corpo.
    preparar_outro_cliente(sessao)
    entrar(http, LOJISTA_OUTRO)

    resposta = http.post(
        f"/clientes/{OUTRO}/resolucoes",
        json={"rodada_id": rodada.id, "lancamento_id": APORTE, "nota": "não é meu"},
    )

    assert resposta.status_code == 404
    entrar(http, LOJISTA_MARINA)
    assert _item(_fechamento(http), APORTE)["resolucao"] is None


def test_suporte_nao_resolve_pendencia(sessao: Session, http: TestClient, rodada: Rodada):
    criar_suporte(sessao)
    entrar(http, SUPORTE)

    assert _resolver(http, rodada.id, APORTE).status_code == 403
    assert http.delete(f"/clientes/{MARINA}/resolucoes/{APORTE}").status_code == 403


def test_suporte_ve_quem_resolveu(sessao: Session, lojista: TestClient, rodada: Rodada):
    _resolver(lojista, rodada.id, APORTE)
    criar_suporte(sessao)
    entrar(lojista, SUPORTE)

    resolucao = _item(_fechamento(lojista), APORTE)["resolucao"]

    assert resolucao["quem"] == LOJISTA_MARINA
    assert resolucao["nota"] == "aporte do sócio"
