"""API HTTP de leitura. As rotas só repassam: a montagem fica em `sinkfi.leitura`.

O contrato desta API vira `web/src/api.d.ts` (ADR 0004). Mudou um esquema, regere o arquivo.
"""

from fastapi import FastAPI

from sinkfi.api import fechamento
from sinkfi.api.sessao import obter_sessao

app = FastAPI(title="sinkfi")
app.include_router(fechamento.rotas)

__all__ = ["app", "obter_sessao"]
