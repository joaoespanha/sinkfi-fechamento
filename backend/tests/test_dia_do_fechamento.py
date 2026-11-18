"""Dia do fechamento por cliente (ADR 0006): o corte vem da configuração e entra no hash."""

from dataclasses import replace
from datetime import date, datetime, time, timedelta

from sinkfi.rodadas import fechamento_vigente, hash_da_rodada
from sinkfi.tipos import ConfigFechamento, Entrada

from tests.construtores import CORTE, LOJAS, SAO_PAULO, em_sao_paulo, lancamento, recebivel

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


def test_hash_nao_depende_da_ordem_dos_recebiveis_com_o_mesmo_id():
    # O banco não garante a ordem; a Stone e a PagSeguro usam o mesmo id (ADR 0009).
    da_stone = recebivel("rec_1", liquidacao_prevista=date(2026, 11, 9), liquido_centavos=1000, nsu="STN-1")
    da_pagseguro = replace(da_stone, adquirente="pagseguro", nsu="PAG-1")

    uma_ordem = Entrada(recebiveis=[da_stone, da_pagseguro], lancamentos=[], lojas=[])
    outra_ordem = Entrada(recebiveis=[da_pagseguro, da_stone], lancamentos=[], lojas=[])

    assert hash_da_rodada(uma_ordem, CORTE, "1") == hash_da_rodada(outra_ordem, CORTE, "1")


def test_entrada_sem_id_repetido_mantem_o_hash_de_antes_da_adquirente_na_chave():
    # O hash foi calculado no código anterior ao ADR 0009 (origin/main 85d72ed). Se mudar, as rodadas
    # gravadas deixam de bater com a entrada e o próximo fechamento cria uma rodada nova sem dado novo.
    entrada = Entrada(
        recebiveis=[
            recebivel("rec_2", liquidacao_prevista=date(2026, 11, 9), liquido_centavos=2000, nsu="STN-2"),
            recebivel("rec_1", liquidacao_prevista=date(2026, 11, 9), liquido_centavos=1000, nsu="STN-1"),
            recebivel(
                "rec_3",
                liquidacao_prevista=date(2026, 11, 9),
                liquido_centavos=3000,
                nsu="PAG-3",
                adquirente="pagseguro",
                loja_id="loja_savassi",
            ),
        ],
        lancamentos=[
            lancamento(
                "ext_1", transacao_id="tx_1", lancado_em=em_sao_paulo(11, 9), valor_centavos=1000, descricao="STONE STN-1"
            )
        ],
        lojas=LOJAS,
    )

    assert hash_da_rodada(entrada, CORTE, "2") == "ba6d260f96f837729f984a9ade79a09125278fab3c21eaf35b3680f1bf84626c"
