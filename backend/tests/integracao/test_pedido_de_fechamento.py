"""Pedido de fechamento (ADR 0004): a fila pode entregar o mesmo pedido duas vezes."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.pedidos import processar_pedido

from tests.integracao.cenarios import MARINA, preparar_marina

# Uma terça à noite: o fechamento vigente é o da segunda, 16/11 às 18h.
AGORA = datetime(2026, 11, 17, 21, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))


def test_pedido_repetido_nao_duplica_rodada(sessao: Session):
    preparar_marina(sessao)

    primeira = processar_pedido(sessao, MARINA, AGORA)
    segunda = processar_pedido(sessao, MARINA, AGORA)

    assert segunda.id == primeira.id
    assert [r.id for r in repositorios.rodadas_do_cliente(sessao, MARINA)] == [primeira.id]
