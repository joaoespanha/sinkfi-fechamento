"""Reproduzir uma rodada gravada (Debugar): a entrada ainda é a mesma, a versão é a de hoje e a regra decide igual."""

from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from fechamento import VERSAO_DA_REGRA, fechar
from sinkfi import reproduzir as modulo
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.reproduzir import reproduzir
from sinkfi.rodadas import rodar_fechamento

from tests.construtores import CORTE
from tests.integracao.cenarios import MARINA, dados_com_recebivel_cancelado, preparar_marina


def test_reproduzir_com_a_mesma_entrada_decide_igual(sessao: Session):
    preparar_marina(sessao)
    rodada = rodar_fechamento(sessao, MARINA, CORTE)

    r = reproduzir(sessao, MARINA, rodada.id)

    assert r.mesma_entrada
    assert r.mesma_versao
    assert r.mudaram == []
    assert r.so_na_gravada == []
    assert r.so_na_de_hoje == []


def test_reproduzir_depois_da_ingestao_aponta_o_que_mudou(sessao: Session, tmp_path: Path):
    preparar_marina(sessao)
    rodada = rodar_fechamento(sessao, MARINA, CORTE)
    ingerir(sessao, MARINA, dados_com_recebivel_cancelado(tmp_path, "rec_1002"))

    r = reproduzir(sessao, MARINA, rodada.id)

    assert not r.mesma_entrada
    assert r.mudaram == ["rec_1002"]


def test_reproduzir_rodada_de_versao_antiga_avisa(sessao: Session):
    preparar_marina(sessao)
    rodada = rodar_fechamento(sessao, MARINA, CORTE, versao="0")

    r = reproduzir(sessao, MARINA, rodada.id)

    assert r.mesma_entrada
    assert not r.mesma_versao
    assert (r.rodada.versao_regra, r.versao_de_hoje) == ("0", VERSAO_DA_REGRA)


def test_reproduzir_aponta_item_que_a_regra_de_hoje_decide_diferente(
    sessao: Session, monkeypatch: pytest.MonkeyPatch
):
    preparar_marina(sessao)
    rodada = rodar_fechamento(sessao, MARINA, CORTE)

    def fechar_com_um_grupo_a_menos(*args, **kwargs):
        fechamento = fechar(*args, **kwargs)
        return replace(fechamento, grupos=fechamento.grupos[1:])

    monkeypatch.setattr(modulo, "fechar", fechar_com_um_grupo_a_menos)

    r = reproduzir(sessao, MARINA, rodada.id)

    assert r.mesma_entrada
    assert len(r.so_na_gravada) == 1
    assert r.so_na_de_hoje == []

