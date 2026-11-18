"""API HTTP. As rotas só repassam: a montagem fica em `sinkfi.leitura`, `sinkfi.rodadas` e `sinkfi.usuarios`.

O contrato desta API vira `web/src/api.d.ts` (ADR 0004). Mudou um esquema, regere o arquivo.
"""

from fastapi import FastAPI

from sinkfi.api import busca_de_clientes, clientes, login, operacao
from sinkfi.api.relogio import obter_agora
from sinkfi.api.sessao import obter_sessao

app = FastAPI(title="sinkfi")
app.include_router(login.rotas)
app.include_router(clientes.rotas)
app.include_router(operacao.rotas)
app.include_router(busca_de_clientes.rotas)

__all__ = ["app", "obter_agora", "obter_sessao"]
