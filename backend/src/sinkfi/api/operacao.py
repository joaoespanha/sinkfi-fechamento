"""A saúde da operação, só para o suporte (Monitorar): o que está parado antes e depois da fila (ADR 0004)."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sinkfi.api.autenticacao import exige_papel
from sinkfi.api.esquemas import OperacaoLida
from sinkfi.api.relogio import obter_agora
from sinkfi.api.sessao import obter_sessao
from sinkfi.banco import repositorios
from sinkfi.fila import Fila, obter_fila
from sinkfi.tipos import Papel

rotas = APIRouter(dependencies=[Depends(exige_papel(Papel.SUPORTE))])


@rotas.get("/operacao")
def ler_operacao(
    sessao: Session = Depends(obter_sessao),
    fila: Fila = Depends(obter_fila),
    agora: datetime = Depends(obter_agora),
) -> OperacaoLida:
    """Pedido parado é o relay fora do ar; mensagem na fila morta é um fechamento que não rodou."""
    parados, mais_antigo = repositorios.pedidos_parados(sessao)
    return OperacaoLida(
        pedidos_parados=parados,
        idade_do_mais_antigo_segundos=int((agora - mais_antigo).total_seconds()) if mais_antigo else None,
        mensagens_na_dead_letter=fila.mensagens_na_dead_letter(),
    )
