"""O ponto único de checagem (ADR 0005): cookie → JWT → usuário do banco → cliente.

O token carrega só a identidade. Papel, cliente e `ativo` vêm do banco a cada requisição.
"""

import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from sinkfi import usuarios
from sinkfi.api.sessao import obter_sessao
from sinkfi.tipos import Papel, Usuario

COOKIE = "sinkfi_sessao"
VALIDADE = timedelta(hours=8)
_ALGORITMO = "HS256"


def _segredo() -> str:
    # Lido na hora: importar o app não exige JWT_SECRET.
    return os.environ["JWT_SECRET"]


def gravar_cookie(resposta: Response, usuario: Usuario) -> None:
    agora = datetime.now(UTC)
    token = jwt.encode(
        {"sub": str(usuario.id), "iat": agora, "exp": agora + VALIDADE}, _segredo(), algorithm=_ALGORITMO
    )
    resposta.set_cookie(
        COOKIE,
        token,
        max_age=int(VALIDADE.total_seconds()),
        httponly=True,
        secure=True,
        samesite="strict",
    )


def apagar_cookie(resposta: Response) -> None:
    resposta.delete_cookie(COOKIE, httponly=True, secure=True, samesite="strict")


def usuario_atual(
    token: str | None = Cookie(default=None, alias=COOKIE),
    sessao: Session = Depends(obter_sessao),
) -> Usuario:
    """401 sem token, com token inválido ou vencido, ou com usuário inativo."""
    if token is None:
        raise HTTPException(status_code=401, detail="sem sessão")
    try:
        dados = jwt.decode(token, _segredo(), algorithms=[_ALGORITMO], options={"require": ["sub", "exp"]})
        usuario = usuarios.usuario_ativo(sessao, int(dados["sub"]))
    except (jwt.InvalidTokenError, ValueError):
        usuario = None
    if usuario is None:
        raise HTTPException(status_code=401, detail="sem sessão")
    return usuario


def checar_cliente(cliente_id: str, usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    """Vai no router de `/clientes/{cliente_id}`: toda rota pendurada nele passa por aqui.

    Cliente de outro dono responde 404, igual a cliente que não existe.
    """
    if usuario.papel is Papel.LOJISTA and usuario.cliente_id != cliente_id:
        raise HTTPException(status_code=404, detail="cliente não encontrado")
    return usuario


def exige_papel(papel: Papel) -> Callable[..., Usuario]:
    """Checagem de papel por rota. Roda depois de `checar_cliente`: outro cliente dá 404, não 403."""

    def checar(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.papel is not papel:
            raise HTTPException(status_code=403, detail="papel sem permissão")
        return usuario

    return checar
