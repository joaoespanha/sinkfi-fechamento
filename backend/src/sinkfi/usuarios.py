"""Usuários e senhas (ADR 0005). A senha só existe aqui: o resto do código vê `Usuario`."""

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.tipos import Papel, Usuario

_hasher = PasswordHasher()
# Conferido quando o email não existe, para a resposta levar o mesmo tempo.
_HASH_DE_NINGUEM = _hasher.hash("ninguem")


def criar_usuario(
    sessao: Session, *, email: str, senha: str, papel: Papel, cliente_id: str | None = None
) -> Usuario:
    return repositorios.gravar_usuario(
        sessao, email=email, senha_hash=_hasher.hash(senha), papel=papel, cliente_id=cliente_id
    )


def desativar_usuario(sessao: Session, email: str) -> None:
    repositorios.desativar_usuario(sessao, email)


def autenticar(sessao: Session, email: str, senha: str) -> Usuario | None:
    """None para email desconhecido, senha errada ou usuário inativo."""
    encontrado = repositorios.usuario_e_hash_por_email(sessao, email)
    usuario, senha_hash = encontrado if encontrado else (None, _HASH_DE_NINGUEM)
    try:
        _hasher.verify(senha_hash, senha)
    except VerificationError:
        return None
    return usuario if usuario and usuario.ativo else None


def usuario_ativo(sessao: Session, id: int) -> Usuario | None:
    """Lido a cada requisição: desativar vale na hora, mesmo com token válido."""
    usuario = repositorios.usuario_por_id(sessao, id)
    return usuario if usuario and usuario.ativo else None
