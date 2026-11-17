"""Dia do fechamento por cliente (ADR 0006): o corte vem da configuração e entra no hash."""

from datetime import datetime, time, timedelta

from sinkfi.rodadas import fechamento_vigente, hash_da_rodada
from sinkfi.tipos import ConfigFechamento, Entrada

from tests.construtores import CORTE, SAO_PAULO

SEGUNDA_18H = ConfigFechamento(dia_fechamento=1, hora_corte=time(18, 0), fuso="America/Sao_Paulo")


def test_fechamento_vigente_de_cliente_de_segunda_na_terca_e_o_da_segunda_anterior():
    # Calendário real: 10/11/2026 é terça. O CORTE do enunciado ("segunda, 10/11") não serve aqui.
    terca = datetime(2026, 11, 10, 10, 0, tzinfo=SAO_PAULO)

    assert fechamento_vigente(SEGUNDA_18H, terca) == datetime(2026, 11, 9, 18, 0, tzinfo=SAO_PAULO)


def test_cliente_de_sexta_tem_corte_na_sexta():
    sexta_18h = ConfigFechamento(dia_fechamento=5, hora_corte=time(18, 0), fuso="America/Sao_Paulo")
    sabado = datetime(2026, 11, 14, 10, 0, tzinfo=SAO_PAULO)

    assert fechamento_vigente(sexta_18h, sabado) == datetime(2026, 11, 13, 18, 0, tzinfo=SAO_PAULO)


def test_corte_diferente_gera_hash_diferente():
    entrada = Entrada(recebiveis=[], lancamentos=[], lojas=[])
    semana_seguinte = CORTE + timedelta(days=7)

    assert hash_da_rodada(entrada, CORTE, "1") != hash_da_rodada(entrada, semana_seguinte, "1")
