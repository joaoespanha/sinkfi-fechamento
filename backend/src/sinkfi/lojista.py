"""O que a lojista faz na tela além de ler: mudar o limite, marcar o fechamento como conferido (ADR 0005, #12)
e resolver uma pendência para conferir (ADR 0014).

Nada aqui cria rodada nem passa pela fila. Cada ação deixa um registro só de inserção.
Como os outros serviços, não faz commit: quem chama é dono da transação.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from fechamento import Severidade
from sinkfi.banco import repositorios
from sinkfi.leitura import fechamento_da_rodada
from sinkfi.tipos import Conferencia, Resolucao, Usuario


def mudar_limite(sessao: Session, cliente_id: str, usuario: Usuario, limite_trava_centavos: int | None) -> None:
    """None desliga a trava (ADR 0003). Muda o limite e registra de quanto para quanto."""
    antes = repositorios.limite_do_cliente(sessao, cliente_id)
    repositorios.definir_limite(sessao, cliente_id, limite_trava_centavos)
    repositorios.gravar_mudanca_limite(
        sessao,
        cliente_id=cliente_id,
        usuario_id=usuario.id,
        em=_agora(),
        de=antes,
        para=limite_trava_centavos,
    )


def conferir(sessao: Session, cliente_id: str, usuario: Usuario, rodada_id: int) -> Conferencia | None:
    """Grava a rodada que a lojista viu, com o limite e o resumo de agora.

    None quando a rodada não é do cliente. Não bloqueia rodada nova.
    """
    rodada = repositorios.rodada_do_cliente(sessao, cliente_id, rodada_id)
    if rodada is None:
        return None
    lido = fechamento_da_rodada(sessao, rodada)
    conferencia = Conferencia(
        quem=usuario.email,
        em=_agora(),
        rodada_id=rodada.id,
        limite_trava_centavos=lido.limite_trava_centavos,
        resumo=lido.resumo,
    )
    repositorios.gravar_conferencia(
        sessao,
        cliente_id=cliente_id,
        usuario_id=usuario.id,
        em=conferencia.em,
        rodada_id=conferencia.rodada_id,
        limite_trava_centavos=conferencia.limite_trava_centavos,
        resumo=conferencia.resumo,
    )
    return conferencia


class PendenciaNaoEncontrada(Exception):
    """A rodada não é do cliente, ou o lançamento não é um item de pendência dela."""


class PendenciaNaoSeResolve(Exception):
    """Só a pendência para conferir se resolve: a falta de verdade, não (ADR 0014)."""


def resolver(
    sessao: Session, cliente_id: str, usuario: Usuario, rodada_id: int, lancamento_id: str, nota: str
) -> Resolucao:
    """Grava a resolução presa ao lançamento e ao valor da pendência na rodada que a tela mostra.

    A rodada é procurada dentro do cliente, e o valor e a severidade vêm do item dela, nunca do corpo.
    """
    rodada = repositorios.rodada_do_cliente(sessao, cliente_id, rodada_id)
    item = next(
        (
            i
            for i in (repositorios.itens_da_rodada(sessao, rodada.id) if rodada else [])
            if not i.recebiveis and i.severidade and [c.id for c in i.creditos] == [lancamento_id]
        ),
        None,
    )
    if item is None or item.pendencia_centavos is None:
        raise PendenciaNaoEncontrada
    if item.severidade is not Severidade.PARA_CONFERIR:
        raise PendenciaNaoSeResolve
    resolucao = Resolucao(
        lancamento_id=lancamento_id,
        valor_centavos=item.pendencia_centavos,
        quem=usuario.email,
        em=_agora(),
        nota=nota,
    )
    repositorios.gravar_resolucao(
        sessao,
        cliente_id=cliente_id,
        lancamento_id=lancamento_id,
        usuario_id=usuario.id,
        em=resolucao.em,
        valor_centavos=resolucao.valor_centavos,
        nota=nota,
    )
    return resolucao


def desfazer(sessao: Session, cliente_id: str, usuario: Usuario, lancamento_id: str) -> bool:
    """Grava a desfeita da resolução em vigor; nada é apagado. False quando o lançamento não tem resolução."""
    if lancamento_id not in repositorios.resolucoes_do_cliente(sessao, cliente_id):
        return False
    repositorios.gravar_desfeita(
        sessao, cliente_id=cliente_id, lancamento_id=lancamento_id, usuario_id=usuario.id, em=_agora()
    )
    return True


def _agora() -> datetime:
    # Hora do Python, não `now()` do Postgres: dois registros na mesma transação não empatam.
    return datetime.now(UTC)
