"""O que a lojista faz na tela além de ler: mudar o limite e marcar "Terminei" (ADR 0005, #12).

Nada aqui cria rodada nem passa pela fila. Cada ação deixa um registro só de inserção.
Como os outros serviços, não faz commit: quem chama é dono da transação.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.leitura import fechamento_da_rodada
from sinkfi.tipos import Termino, Usuario


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


def terminar(sessao: Session, cliente_id: str, usuario: Usuario, rodada_id: int) -> Termino | None:
    """Grava a rodada que a lojista viu, com o limite e o resumo de agora.

    None quando a rodada não é do cliente. Não bloqueia rodada nova.
    """
    rodada = repositorios.rodada_do_cliente(sessao, cliente_id, rodada_id)
    if rodada is None:
        return None
    lido = fechamento_da_rodada(sessao, rodada)
    termino = Termino(
        quem=usuario.email,
        em=_agora(),
        rodada_id=rodada.id,
        limite_trava_centavos=lido.limite_trava_centavos,
        resumo=lido.resumo,
    )
    repositorios.gravar_termino(
        sessao,
        cliente_id=cliente_id,
        usuario_id=usuario.id,
        em=termino.em,
        rodada_id=termino.rodada_id,
        limite_trava_centavos=termino.limite_trava_centavos,
        resumo=termino.resumo,
    )
    return termino


def _agora() -> datetime:
    # Hora do Python, não `now()` do Postgres: dois registros na mesma transação não empatam.
    return datetime.now(UTC)
