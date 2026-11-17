"""Os cortes que a lojista pode escolher e o fechamento atual (ADR 0007). Sem banco.

Um corte cobre os dias depois do corte anterior até o dia dele. Para achar o fechamento atual,
o recebível previsto e o crédito lançado contam pela data no fuso do cliente: o crédito de 10/11
às 19:00 é de 10/11. O fechamento atual só decide onde a tela abre; a rodada usa o horário.
"""

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sinkfi.rodadas import fechamento_vigente
from sinkfi.tipos import ConfigFechamento, ItemRodada

SEMANA = timedelta(days=7)


def corte_vigente(config: ConfigFechamento, agora: datetime, ancora: datetime | None = None) -> datetime:
    """O último corte que já passou. Com a âncora, de 7 em 7 dias a partir dela; sem, o dia do cliente."""
    if ancora is None:
        return fechamento_vigente(config, agora)
    # A âncora só fixa o dia e a hora: os cortes vão para trás e para a frente no mesmo passo.
    semanas = (agora - ancora) // SEMANA
    return ancora.astimezone(ZoneInfo(config.fuso)) + semanas * SEMANA


def cortes(
    config: ConfigFechamento, agora: datetime, primeira_data: date | None, ancora: datetime | None = None
) -> list[datetime]:
    """Do primeiro corte que cobre a primeira liquidação prevista até o vigente, do mais antigo ao mais novo."""
    if primeira_data is None:
        return []
    corte = corte_vigente(config, agora, ancora)
    lista = []
    while corte.date() >= primeira_data:
        lista.append(corte)
        corte -= SEMANA
    return lista[::-1]


def fechamento_atual(cortes: list[datetime], datas_com_dado: Iterable[date]) -> datetime | None:
    """O corte mais recente com dado nos seus dias. None quando nenhum corte tem dado."""
    datas = list(datas_com_dado)
    for i in range(len(cortes) - 1, -1, -1):
        anterior = cortes[i - 1].date() if i > 0 else date.min
        if any(anterior < d <= cortes[i].date() for d in datas):
            return cortes[i]
    return None


def dias_da_semana(data_fechamento: date) -> list[date]:
    """Os 7 dias do fechamento: do dia seguinte ao corte anterior até o dia do corte."""
    return [data_fechamento - timedelta(days=n) for n in range(6, -1, -1)]


def dia_do_item(item: ItemRodada, corte: datetime, fuso: ZoneInfo) -> date | None:
    """O dia da semana em que o item aparece. None = antes desta semana.

    Venda ou grupo: a última liquidação prevista (ADR 0002). Crédito sem venda: a data em que
    caiu, no fuso do cliente. O crédito depois do corte anterior, no mesmo dia dele, entra no
    primeiro dia; o depois do corte, no último.
    """
    dias = dias_da_semana(corte.astimezone(fuso).date())
    if item.recebiveis:
        dia = max(r.liquidacao_prevista for r in item.recebiveis)
        return dia if dia >= dias[0] else None
    lancado_em = item.creditos[0].lancado_em
    if lancado_em <= corte - SEMANA:
        return None
    return min(max(lancado_em.astimezone(fuso).date(), dias[0]), dias[-1])
