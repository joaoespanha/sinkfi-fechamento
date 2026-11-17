"""Em que dia da semana aparece cada item do fechamento (#26). Sem banco.

Corte de terça, 10/11, às 18:00: a semana vai de quarta, 04/11, a terça, 10/11.
"""

from datetime import date, timedelta

from sinkfi.semanas import dia_do_item, dias_da_semana
from sinkfi.tipos import ItemRodada

from tests.construtores import CORTE, SAO_PAULO, em_sao_paulo, lancamento, recebivel


def _venda(id: str, prevista: date):
    return recebivel(id, liquidacao_prevista=prevista, liquido_centavos=10_000, nsu=f"nsu_{id}")


def _credito(id: str, lancado_em):
    return lancamento(id, transacao_id=f"tx_{id}", lancado_em=lancado_em, valor_centavos=10_000, descricao="PIX")


def test_dias_da_semana_vao_do_dia_seguinte_ao_corte_anterior_ate_o_corte():
    dias = dias_da_semana(date(2026, 11, 10))

    assert dias == [date(2026, 11, 4) + timedelta(days=n) for n in range(7)]
    assert dias[0].isoweekday() == 3  # quarta
    assert dias[-1] == date(2026, 11, 10)


def test_venda_aparece_no_dia_previsto():
    # Prevista na sexta, 06/11; o dinheiro caiu na segunda, 09/11. Vale o dia previsto.
    item = ItemRodada(recebiveis=[_venda("r1", date(2026, 11, 6))], creditos=[_credito("c1", em_sao_paulo(11, 9))])

    assert dia_do_item(item, CORTE, SAO_PAULO) == date(2026, 11, 6)


def test_credito_sem_venda_aparece_no_dia_em_que_caiu():
    # Domingo, 08/11, às 23:30 de São Paulo, que já é segunda em UTC.
    item = ItemRodada(recebiveis=[], creditos=[_credito("c1", em_sao_paulo(11, 8, 23, 30))])
    assert dia_do_item(item, CORTE, SAO_PAULO) == date(2026, 11, 8)

    # Terça, 03/11, às 19:00: depois do corte anterior, então é desta semana e entra no primeiro dia.
    depois_do_corte_anterior = ItemRodada(recebiveis=[], creditos=[_credito("c2", em_sao_paulo(11, 3, 19))])
    assert dia_do_item(depois_do_corte_anterior, CORTE, SAO_PAULO) == date(2026, 11, 4)

    # Terça, 03/11, às 17:00: antes do corte anterior.
    antes_do_corte_anterior = ItemRodada(recebiveis=[], creditos=[_credito("c3", em_sao_paulo(11, 3, 17))])
    assert dia_do_item(antes_do_corte_anterior, CORTE, SAO_PAULO) is None


def test_grupo_aparece_no_dia_da_ultima_venda_prevista():
    # ADR 0002: um crédito pagou vendas previstas na quinta e no sábado.
    item = ItemRodada(
        recebiveis=[_venda("r1", date(2026, 11, 5)), _venda("r2", date(2026, 11, 7))],
        creditos=[_credito("c1", em_sao_paulo(11, 7))],
    )

    assert dia_do_item(item, CORTE, SAO_PAULO) == date(2026, 11, 7)


def test_falta_de_semana_anterior_fica_em_antes_desta_semana():
    # Prevista na terça, 03/11, o dia do corte anterior, e não caiu: a regra é acumulada.
    item = ItemRodada(recebiveis=[_venda("r1", date(2026, 11, 3))], creditos=[])

    assert dia_do_item(item, CORTE, SAO_PAULO) is None
