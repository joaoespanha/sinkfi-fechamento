"""Os fechamentos de um cliente (ADR 0007): a lista de cortes, o fechamento atual e o aviso.

A api e o worker usam o mesmo `corte_atual`. Não faz commit.
"""

import os
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.leitura import fechamento_da_rodada
from sinkfi.semanas import corte_vigente, cortes, fechamento_atual


def ancora_dos_cortes() -> datetime | None:
    """Só na demonstração: os CSVs batem com o corte de terça, 10/11, e a Marina fecha na segunda."""
    valor = os.environ.get("SINKFI_ANCORA_DOS_CORTES")
    return datetime.fromisoformat(valor) if valor else None


@dataclass(frozen=True)
class Semana:
    semana: date
    corte: datetime
    atual: bool
    tem_rodada: bool
    # Da rodada mais recente do corte; None sem rodada.
    itens_falta_de_verdade: int | None
    itens_para_conferir: int | None
    # A rodada mais recente do corte tem conferência.
    conferido: bool
    # Anterior ao atual, com rodada, com pendência e sem término (ADR 0003: não é estado, é leitura).
    aviso: bool


def cortes_do_cliente(
    sessao: Session, cliente_id: str, agora: datetime, ancora: datetime | None
) -> tuple[list[datetime], datetime | None]:
    """Os cortes que já passaram, do mais antigo ao mais novo, e o corte atual. Vazio para cliente desconhecido."""
    config = repositorios.config_do_cliente(sessao, cliente_id)
    if config is None:
        return [], None
    entrada = repositorios.entrada_do_cliente(sessao, cliente_id)
    previstas = [r.liquidacao_prevista for r in entrada.recebiveis]
    fuso = ZoneInfo(config.fuso)
    creditos = [l.lancado_em.astimezone(fuso).date() for l in entrada.lancamentos if l.valor_centavos > 0]
    lista = cortes(config, agora, min(previstas, default=None), ancora)
    # Sem dado em nenhum corte, vale o vigente pelo relógio.
    atual = fechamento_atual(lista, [*previstas, *creditos]) or corte_vigente(config, agora, ancora)
    return lista, atual


def corte_atual(sessao: Session, cliente_id: str, agora: datetime, ancora: datetime | None) -> datetime | None:
    """None só para cliente desconhecido."""
    return cortes_do_cliente(sessao, cliente_id, agora, ancora)[1]


def corte_da_semana(
    sessao: Session, cliente_id: str, agora: datetime, ancora: datetime | None, semana: date
) -> datetime | None:
    """O corte daquela data, se ele está na lista. None fora dela."""
    lista, _ = cortes_do_cliente(sessao, cliente_id, agora, ancora)
    return next((c for c in lista if c.date() == semana), None)


def fechamentos_do_cliente(
    sessao: Session, cliente_id: str, agora: datetime, ancora: datetime | None
) -> list[Semana]:
    """Do mais novo para o mais antigo."""
    lista, atual = cortes_do_cliente(sessao, cliente_id, agora, ancora)
    # Da rodada mais recente para a mais antiga: a primeira de cada data é a que vale.
    mais_recente = {}
    for rodada in repositorios.rodadas_do_cliente(sessao, cliente_id):
        mais_recente.setdefault(rodada.data_fechamento, rodada)
    conferidas = {t.rodada_id for t in repositorios.conferencias_do_cliente(sessao, cliente_id)}

    semanas = []
    for corte in reversed(lista):
        rodada = mais_recente.get(corte.date())
        if rodada is None:
            semanas.append(Semana(corte.date(), corte, corte == atual, False, None, None, False, False))
            continue
        resumo = fechamento_da_rodada(sessao, rodada).resumo
        pendencias = resumo.itens_falta_de_verdade + resumo.itens_para_conferir
        conferido = rodada.id in conferidas
        semanas.append(
            Semana(
                semana=corte.date(),
                corte=corte,
                atual=corte == atual,
                tem_rodada=True,
                itens_falta_de_verdade=resumo.itens_falta_de_verdade,
                itens_para_conferir=resumo.itens_para_conferir,
                conferido=conferido,
                aviso=atual is not None and corte < atual and pendencias > 0 and not conferido,
            )
        )
    return semanas
