"""A saúde da aplicação: a api fala com o Postgres e com o broker? Sem login, para o health check do compose.

`/health`, em inglês por exceção: é o nome que load balancers e sondas procuram por convenção.
Diz só o que caiu: sem versão, host nem a mensagem do erro, porque a rota é aberta.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from sinkfi.api.sessao import obter_sessao
from sinkfi.fila import Fila, obter_fila

rotas = APIRouter()


@rotas.get("/health")
def ler_saude(sessao: Session = Depends(obter_sessao), fila: Fila = Depends(obter_fila)) -> JSONResponse:
    dependencias = {
        "postgres": "ok" if _banco_responde(sessao) else "falhou",
        "broker": "ok" if fila.broker_responde() else "falhou",
    }
    no_ar = all(estado == "ok" for estado in dependencias.values())
    return JSONResponse({"status": "ok" if no_ar else "falhou", **dependencias}, status_code=200 if no_ar else 503)


def _banco_responde(sessao: Session) -> bool:
    try:
        sessao.execute(text("select 1"))
        return True
    except SQLAlchemyError:
        return False
