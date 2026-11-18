"""A atualização dos dados (ADR 0011): quando foi a última ingestão e quando vem a próxima.

A agenda mora aqui: o beat (`tarefas.py`) e a leitura usam as mesmas horas.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

# As horas UTC da ingestão; em São Paulo, 21h, 3h, 9h e 15h.
HORAS_DA_INGESTAO = (0, 6, 12, 18)
# Dois ciclos sem ingestão: um só pode ser o worker fora, e a próxima cobre.
ATRASO = timedelta(hours=12)


@dataclass(frozen=True)
class Atualizacao:
    # None = o cliente nunca teve ingestão.
    ultima_em: datetime | None
    # Prevista: uma execução que vence com o worker fora não roda, e a próxima cobre.
    proxima_prevista_em: datetime
    atrasada: bool
    # Só quando atrasada: a primeira prevista depois da última que não aconteceu.
    primeira_perdida_em: datetime | None


def proxima_prevista(depois_de: datetime) -> datetime:
    """A primeira hora da agenda estritamente depois de `depois_de`. Em cima da hora, a seguinte."""
    utc = depois_de.astimezone(UTC)
    dia = utc.replace(hour=0, minute=0, second=0, microsecond=0)
    for hora in HORAS_DA_INGESTAO:
        if (candidata := dia.replace(hour=hora)) > utc:
            return candidata
    return dia + timedelta(days=1, hours=HORAS_DA_INGESTAO[0])


def atualizacao(ultima_em: datetime | None, agora: datetime) -> Atualizacao:
    atrasada = ultima_em is not None and agora - ultima_em > ATRASO
    return Atualizacao(
        ultima_em=ultima_em,
        proxima_prevista_em=proxima_prevista(agora),
        atrasada=atrasada,
        primeira_perdida_em=proxima_prevista(ultima_em) if atrasada and ultima_em else None,
    )
