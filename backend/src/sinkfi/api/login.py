"""Entrar, sair e quem sou eu (ADR 0005). O resto da autenticação está em `autenticacao`."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from sinkfi import usuarios
from sinkfi.api.autenticacao import apagar_cookie, gravar_cookie, usuario_atual
from sinkfi.api.esquemas import EuResposta, LoginEntrada
from sinkfi.api.sessao import obter_sessao
from sinkfi.tipos import Usuario

rotas = APIRouter()


@rotas.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def entrar(entrada: LoginEntrada, resposta: Response, sessao: Session = Depends(obter_sessao)) -> None:
    usuario = usuarios.autenticar(sessao, entrada.email, entrada.senha)
    if usuario is None:
        # A mesma resposta para email desconhecido e senha errada.
        raise HTTPException(status_code=401, detail="email ou senha inválidos")
    gravar_cookie(resposta, usuario)


@rotas.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def sair(resposta: Response) -> None:
    apagar_cookie(resposta)


@rotas.get("/eu")
def eu(usuario: Usuario = Depends(usuario_atual)) -> EuResposta:
    return EuResposta(email=usuario.email, papel=usuario.papel, cliente_id=usuario.cliente_id)
