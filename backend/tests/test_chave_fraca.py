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


def test_credito_que_casa_so_com_recebivel_a_vencer_pode_ser_antecipacao():
    # Caso construído: previsto para 11/11, depois do corte. O crédito cai em 10/11 (D-1).
    a_vencer = rec_1002(liquidacao_prevista=date(2026, 11, 11), vendido_em=date(2026, 11, 8))

    fechamento = fechar(
        recebiveis=[a_vencer],
        lancamentos=[t_1002(em_sao_paulo(11, 10, 10))],
        lojas=LOJAS,
        corte=CORTE,
    )

    # O recebível é a vencer e fica fora dos grupos, mas o crédito não some do relatório.
    assert fechamento.grupos == []
    [pendencia] = fechamento.pendencias
    assert pendencia.motivo == Motivo.PODE_SER_ANTECIPACAO
    assert pendencia.severidade == Severidade.PARA_CONFERIR
    assert pendencia.valor_centavos == 87714
    assert pendencia.lancamento.id == "ext_03"


def rec_3000(id: str):
    return recebivel(id, liquidacao_prevista=date(2026, 11, 9), liquido_centavos=210000, nsu=f"STN-{id[-4:]}")


def t_3000(id: str, hora: int):
    return lancamento(
        id, transacao_id=f"T-{id}", lancado_em=em_sao_paulo(11, 9, hora), valor_centavos=210000, descricao="stone"
    )


def test_empate_com_dois_creditos_fecha_o_grupo():
    # Duas vendas de 2.100,00 no mesmo dia e dois créditos sem NSU: todo o dinheiro caiu.
    fechamento = fechar(
        recebiveis=[rec_3000("rec_3001"), rec_3000("rec_3002")],
        lancamentos=[t_3000("ext_05", 13), t_3000("ext_70", 14)],
        lojas=LOJAS,
        corte=CORTE,
    )

    [grupo] = fechamento.grupos
    assert {c.id for c in grupo.creditos} == {"ext_05", "ext_70"}
    assert grupo.caiu_centavos == grupo.esperado_centavos == 420000
    assert fechamento.pendencias == []


def test_credito_sem_nsu_alem_dos_recebiveis_fica_para_conferir():
    # Um recebível e dois créditos iguais: o segundo pode ser uma venda que falta no arquivo da adquirente.
    fechamento = fechar(
        recebiveis=[rec_3000("rec_3001")],
        lancamentos=[t_3000("ext_05", 13), t_3000("ext_70", 14)],
        lojas=LOJAS,
        corte=CORTE,
    )

    [grupo] = fechamento.grupos
    assert [c.id for c in grupo.creditos] == ["ext_05"]
    assert grupo.caiu_centavos == 210000
    [pendencia] = fechamento.pendencias
    assert pendencia.motivo == Motivo.ENTRADA_SEM_RECEBIVEL
    assert pendencia.severidade == Severidade.PARA_CONFERIR
    assert pendencia.lancamento.id == "ext_70"
