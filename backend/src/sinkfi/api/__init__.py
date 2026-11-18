"""API HTTP. As rotas só repassam: a montagem fica em `sinkfi.leitura`, `sinkfi.rodadas` e `sinkfi.usuarios`.

O contrato desta API vira `web/src/api.d.ts` (ADR 0004). Mudou um esquema, regere o arquivo.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sinkfi.api import busca_de_clientes, clientes, login, operacao, saude
from sinkfi.api.autenticacao import conferir_segredo
from sinkfi.api.relogio import obter_agora
from sinkfi.api.sessao import obter_sessao


@asynccontextmanager
async def _subida(_: FastAPI) -> AsyncIterator[None]:
    # Na subida, e não no import: exportar o OpenAPI não precisa de segredo. Segredo ruim, a api nem sobe.
    conferir_segredo()
    yield


app = FastAPI(title="sinkfi", lifespan=_subida)
app.include_router(login.rotas)
app.include_router(clientes.rotas)
app.include_router(operacao.rotas)
app.include_router(busca_de_clientes.rotas)
app.include_router(saude.rotas)

__all__ = ["app", "obter_agora", "obter_sessao"]
