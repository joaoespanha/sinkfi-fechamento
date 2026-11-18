"""Rodada imutável (ADR 0004): a mesma entrada não gera outra rodada."""

import logging
from pathlib import Path

import pytest

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.rodadas import rodar_fechamento

from tests.construtores import CORTE
from tests.integracao.cenarios import MARINA, dados_com_credito_a_mais, preparar_marina


def test_mesma_entrada_devolve_a_rodada_que_ja_existe(sessao: Session):
    preparar_marina(sessao)

    primeira = rodar_fechamento(sessao, MARINA, CORTE)
    segunda = rodar_fechamento(sessao, MARINA, CORTE)

    assert segunda.id == primeira.id


def test_entrada_nova_cria_rodada_e_guarda_a_anterior(sessao: Session, tmp_path: Path):
    preparar_marina(sessao)
    anterior = rodar_fechamento(sessao, MARINA, CORTE)

    ingerir(sessao, MARINA, dados_com_credito_a_mais(tmp_path))
    nova = rodar_fechamento(sessao, MARINA, CORTE)

    assert nova.id != anterior.id
    assert [r.id for r in repositorios.rodadas_do_cliente(sessao, MARINA)] == [nova.id, anterior.id]


def test_rodada_registra_no_log_se_e_nova_ou_existente(sessao: Session, caplog: pytest.LogCaptureFixture):
    preparar_marina(sessao)

    with caplog.at_level(logging.INFO, logger="sinkfi.rodadas"):
        rodada = rodar_fechamento(sessao, MARINA, CORTE)
        rodar_fechamento(sessao, MARINA, CORTE)

    nova, existente = [r.getMessage() for r in caplog.records if r.name == "sinkfi.rodadas"]
    assert f"rodada {rodada.id} nova" in nova
    assert f"rodada {rodada.id} existente" in existente
    for mensagem in (nova, existente):
        assert MARINA in mensagem
        assert f"versão {rodada.versao_regra}" in mensagem
        assert "corte 2026-11-10T18:00:00-03:00" in mensagem
