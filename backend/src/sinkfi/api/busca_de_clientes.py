"""A busca do suporte por um cliente: e-mail da lojista, CNPJ ou nome (ADR 0010)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import StringConstraints
from sqlalchemy.orm import Session

from sinkfi.api.autenticacao import exige_papel
from sinkfi.api.esquemas import ClienteEncontradoLido
from sinkfi.api.sessao import obter_sessao
from sinkfi.banco import repositorios
from sinkfi.tipos import Papel

LIMITE = 10
# Contado depois de tirar os espaços. Com menos, a resposta é 422.
Termo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3)]

# No router, e não por rota depois de `checar_cliente`: o caminho não tem cliente. A barreira é o papel.
rotas = APIRouter(dependencies=[Depends(exige_papel(Papel.SUPORTE))])


@rotas.get("/clientes")
def buscar_clientes(
    busca: Annotated[Termo, Query(description="E-mail da lojista, CNPJ (com ou sem pontuação) ou nome.")],
    sessao: Session = Depends(obter_sessao),
) -> list[ClienteEncontradoLido]:
    return [
        ClienteEncontradoLido.model_validate(cliente)
        for cliente in repositorios.buscar_clientes(sessao, busca, LIMITE)
    ]
