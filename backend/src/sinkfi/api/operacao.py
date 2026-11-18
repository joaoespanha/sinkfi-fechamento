"""A saúde da operação, só para o suporte (Monitorar): o que está parado antes e depois da fila (ADR 0004)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sinkfi.api.autenticacao import exige_papel
from sinkfi.api.esquemas import OperacaoLida
from sinkfi.api.sessao import obter_sessao
from sinkfi.banco import repositorios
from sinkfi.fila import Fila, obter_fila
from sinkfi.tipos import Papel

# No router, e não por rota depois de `checar_cliente`: o caminho não tem cliente.
rotas = APIRouter(dependencies=[Depends(exige_papel(Papel.SUPORTE))])


@rotas.get("/operacao")
def ler_operacao(
    sessao: Session = Depends(obter_sessao),
    fila: Fila = Depends(obter_fila),
) -> OperacaoLida:
    """Pedido pendente há minutos é o relay fora do ar; mensagem na fila morta é trabalho que falhou de vez."""
    pendentes, idade = repositorios.pedidos_pendentes(sessao)
    return OperacaoLida(
        pedidos_pendentes=pendentes,
        idade_do_mais_antigo_segundos=idade,
        mensagens_na_dead_letter=fila.mensagens_na_dead_letter(),
    )
