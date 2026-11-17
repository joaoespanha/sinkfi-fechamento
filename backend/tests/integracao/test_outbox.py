"""Outbox da ingestão (ADR 0004): o pedido de fechamento nasce na transação do dado e o relay publica cada um uma vez."""

from datetime import time

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.outbox import publicar_pendentes

from tests.integracao.cenarios import DADOS, MARINA, FilaFalsa, preparar_marina


def test_ingestao_grava_dado_e_pedido_na_mesma_transacao(sessao: Session):
    repositorios.criar_cliente(
        sessao, id=MARINA, nome="Marina", dia_fechamento=1, hora_corte=time(18, 0), fuso="America/Sao_Paulo"
    )

    ingestao = sessao.begin_nested()
    ingerir(sessao, MARINA, DADOS)
    assert repositorios.entrada_do_cliente(sessao, MARINA).lancamentos
    ingestao.rollback()

    # Desfeita a ingestão, o pedido some junto com o dado: não sobra pedido sem dado.
    fila = FilaFalsa()
    publicar_pendentes(sessao, fila)
    assert repositorios.entrada_do_cliente(sessao, MARINA).lancamentos == []
    assert fila.fechamentos == []

    # Sem o rollback, os dois ficam.
    ingerir(sessao, MARINA, DADOS)
    publicar_pendentes(sessao, fila)
    assert repositorios.entrada_do_cliente(sessao, MARINA).lancamentos
    assert fila.fechamentos == [MARINA]


def test_relay_nao_publica_o_mesmo_pedido_em_duas_execucoes(sessao: Session):
    preparar_marina(sessao)
    fila = FilaFalsa()

    publicar_pendentes(sessao, fila)
    publicar_pendentes(sessao, fila)

    assert fila.fechamentos == [MARINA]
