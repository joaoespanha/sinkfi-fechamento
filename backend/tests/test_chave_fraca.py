"""Janela da chave fraca: de max(venda, previsto - 1) até previsto + 4, em dias corridos."""

from datetime import date

from fechamento import Motivo, Severidade, fechar

from tests.construtores import CORTE, LOJAS, PAGSEGURO, em_sao_paulo, lancamento, recebivel


def rec_1002(liquidacao_prevista=date(2026, 11, 6), vendido_em=date(2026, 11, 4)):
    return recebivel(
        "rec_1002",
        vendido_em=vendido_em,
        liquidacao_prevista=liquidacao_prevista,
        liquido_centavos=87714,
        nsu="STN-1002",
    )


def t_1002(dia):
    # Crédito da Stone sem NSU na descrição.
    return lancamento(
        "ext_03",
        transacao_id="T-1002",
        lancado_em=dia,
        valor_centavos=87714,
        descricao="vendas stone novembro",
    )


def test_chave_fraca_casa_credito_no_dia_previsto():
    fechamento = fechar(
        recebiveis=[rec_1002()],
        lancamentos=[t_1002(em_sao_paulo(11, 6, 15, 11, 40))],
        lojas=LOJAS,
        corte=CORTE,
    )

    [grupo] = fechamento.grupos
    assert grupo.caiu_centavos == 87714
    assert fechamento.pendencias == []


def test_chave_fraca_casa_credito_um_dia_antes():
    fechamento = fechar(
        recebiveis=[rec_1002()],
        lancamentos=[t_1002(em_sao_paulo(11, 5))],
        lojas=LOJAS,
        corte=CORTE,
    )

    [grupo] = fechamento.grupos
    assert grupo.caiu_centavos == 87714
    assert fechamento.pendencias == []


def test_chave_fraca_nao_casa_credito_depois_da_janela():
    # Caso construído: previsto para 03/11, o crédito cai em 08/11 (D+5).
    fechamento = fechar(
        recebiveis=[rec_1002(liquidacao_prevista=date(2026, 11, 3), vendido_em=date(2026, 11, 1))],
        lancamentos=[t_1002(em_sao_paulo(11, 8))],
        lojas=LOJAS,
        corte=CORTE,
    )

    [grupo] = fechamento.grupos
    assert grupo.caiu_centavos == 0
    assert grupo.nao_caiu_centavos == 87714
    entradas = [p for p in fechamento.pendencias if p.motivo == Motivo.ENTRADA_SEM_RECEBIVEL]
    assert [p.lancamento.id for p in entradas] == ["ext_03"]


def test_chave_fraca_nao_casa_parcela_futura():
    # rec_6001b: parcela 2/3 de 1.773,00, vendida em 04/11, prevista para 04/12.
    rec_6001b = recebivel(
        "rec_6001b",
        adquirente="pagseguro",
        loja_id="loja_savassi",
        vendido_em=date(2026, 11, 4),
        liquidacao_prevista=date(2026, 12, 4),
        liquido_centavos=177300,
        nsu="PAG-6001",
        parcela=2,
        parcelas=3,
    )
    # Crédito da PagSeguro sem NSU, com o mesmo líquido, em 09/11.
    credito = lancamento(
        "ext_x",
        transacao_id="T-X",
        lancado_em=em_sao_paulo(11, 9),
        valor_centavos=177300,
        documento_contraparte=PAGSEGURO,
        descricao="pagseguro loja",
    )

    fechamento = fechar(recebiveis=[rec_6001b], lancamentos=[credito], lojas=LOJAS, corte=CORTE)

    assert fechamento.grupos == []
    [pendencia] = fechamento.pendencias
    assert pendencia.motivo == Motivo.ENTRADA_SEM_RECEBIVEL
    assert pendencia.severidade == Severidade.PARA_CONFERIR
    assert pendencia.lancamento.id == "ext_x"
