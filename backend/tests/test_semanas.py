"""Semanas e fechamento atual (ADR 0007): os cortes que já passaram e o mais recente com dado.

Calendário real: 05/11/2026 é quinta, 09/11 e 16/11 são segundas, 10/11 e 17/11 são terças.
"""

from datetime import date, datetime, time

from sinkfi.semanas import cortes, fechamento_atual
from sinkfi.tipos import ConfigFechamento

from tests.construtores import SAO_PAULO, em_sao_paulo

SEGUNDA_18H = ConfigFechamento(dia_fechamento=1, hora_corte=time(18, 0), fuso="America/Sao_Paulo")
SEXTA_18H = ConfigFechamento(dia_fechamento=5, hora_corte=time(18, 0), fuso="America/Sao_Paulo")
# A âncora da demonstração: o corte do enunciado, terça 10/11 às 18:00.
ANCORA = datetime(2026, 11, 10, 18, 0, tzinfo=SAO_PAULO)


# Semanas


def test_semanas_vao_da_primeira_liquidacao_prevista_ate_a_vigente():
    # Primeira liquidação prevista na quinta, 05/11; agora é terça, 24/11.
    agora = em_sao_paulo(11, 24, 10)

    assert cortes(SEGUNDA_18H, agora, date(2026, 11, 5)) == [
        em_sao_paulo(11, 9, 18),
        em_sao_paulo(11, 16, 18),
        em_sao_paulo(11, 23, 18),
    ]


def test_semana_cujo_corte_nao_passou_fica_fora():
    # Segunda, 23/11, um minuto antes do corte: o de 23/11 ainda não passou.
    agora = em_sao_paulo(11, 23, 17, 59)

    assert cortes(SEGUNDA_18H, agora, date(2026, 11, 5)) == [
        em_sao_paulo(11, 9, 18),
        em_sao_paulo(11, 16, 18),
    ]


def test_com_ancora_os_cortes_andam_de_sete_em_sete_dias():
    agora = em_sao_paulo(11, 24, 21)

    # A âncora numa terça passa por cima do dia de fechamento da Marina (segunda).
    assert cortes(SEGUNDA_18H, agora, date(2026, 11, 5), ancora=ANCORA) == [
        em_sao_paulo(11, 10, 18),
        em_sao_paulo(11, 17, 18),
        em_sao_paulo(11, 24, 18),
    ]
    # Liquidação prevista antes da semana da âncora: os cortes vão para trás no mesmo passo.
    assert cortes(SEGUNDA_18H, agora, date(2026, 11, 1), ancora=ANCORA)[0] == em_sao_paulo(11, 3, 18)


def test_sem_ancora_os_cortes_seguem_a_configuracao_do_cliente():
    # Cliente de sexta às 18:00; agora é sábado, 21/11.
    agora = em_sao_paulo(11, 21, 10)

    assert cortes(SEXTA_18H, agora, date(2026, 11, 5)) == [
        em_sao_paulo(11, 6, 18),
        em_sao_paulo(11, 13, 18),
        em_sao_paulo(11, 20, 18),
    ]


# Fechamento atual

TRES_CORTES = [em_sao_paulo(11, 10, 18), em_sao_paulo(11, 17, 18), em_sao_paulo(11, 24, 18)]


def test_fechamento_atual_e_o_mais_recente_com_recebivel_previsto_ou_credito():
    # Recebível previsto ou crédito lançado na semana de 17/11: os dois chegam como data.
    assert fechamento_atual(TRES_CORTES, [date(2026, 11, 8), date(2026, 11, 15)]) == TRES_CORTES[1]
    # Crédito no dia do corte, mesmo depois das 18:00: é daquele corte. A rodada é que usa o horário.
    assert fechamento_atual(TRES_CORTES, [date(2026, 11, 10)]) == TRES_CORTES[0]
    # Sem dado em nenhum corte (a parcela de 04/12 ainda não tem corte que passou).
    assert fechamento_atual(TRES_CORTES, [date(2026, 12, 4)]) is None


def test_dado_de_semana_mais_recente_muda_o_fechamento_atual():
    dados = [date(2026, 11, 5), date(2026, 11, 10)]
    assert fechamento_atual(TRES_CORTES, dados) == TRES_CORTES[0]

    # Chega um crédito na sexta, 20/11.
    assert fechamento_atual(TRES_CORTES, [*dados, date(2026, 11, 20)]) == TRES_CORTES[2]
