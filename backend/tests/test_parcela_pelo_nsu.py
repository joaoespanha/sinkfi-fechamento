"""Parcela pelo NSU: a regra só olha parcela quando o NSU se repete."""

from datetime import date

from fechamento import Motivo, Severidade, fechar

from tests.construtores import CORTE, LOJAS, PAGSEGURO, em_sao_paulo, lancamento, recebivel


def parcela_6001(n: int, liquidacao_prevista: date):
    """Parcela n/3 de uma venda parcelada da PagSeguro, como o PAG-6001."""
    return recebivel(
        f"rec_6001_{n}",
        adquirente="pagseguro",
        loja_id="loja_savassi",
        vendido_em=date(2026, 9, 4),
        liquidacao_prevista=liquidacao_prevista,
        liquido_centavos=177300,
        nsu="PAG-6001",
        parcela=n,
        parcelas=3,
    )


def credito_6001(id: str, dia, descricao: str):
    return lancamento(
        id,
        transacao_id=f"T-{id}",
        lancado_em=dia,
        valor_centavos=177300,
        documento_contraparte=PAGSEGURO,
        descricao=descricao,
    )


def grupo_da_parcela(fechamento, n: int):
    [grupo] = [g for g in fechamento.grupos if any(r.id == f"rec_6001_{n}" for r in g.recebiveis)]
    return grupo


def test_nsu_de_venda_a_vista_casa_sem_indicacao_de_parcela():
    rec_4812 = recebivel(
        "rec_4812",
        liquidacao_prevista=date(2026, 11, 9),
        liquido_centavos=479000,
        nsu="STN-4812",
    )
    t_4812 = lancamento(
        "ext_04",
        transacao_id="T-4812",
        lancado_em=em_sao_paulo(11, 9, 10, 8, 19),
        valor_centavos=479000,
        descricao="STN-4812",
    )

    fechamento = fechar(recebiveis=[rec_4812], lancamentos=[t_4812], lojas=LOJAS, corte=CORTE)

    [grupo] = fechamento.grupos
    assert grupo.caiu_centavos == 479000
    assert fechamento.pendencias == []


def test_nsu_com_parcela_na_descricao_casa_a_parcela_indicada():
    # Caso construído: a 1/3 e a 2/3 já venceram, e o crédito diz "2/3".
    parcelas = [
        parcela_6001(1, date(2026, 10, 6)),
        parcela_6001(2, date(2026, 11, 6)),
        parcela_6001(3, date(2026, 12, 4)),
    ]
    credito = credito_6001("ext_a", em_sao_paulo(11, 6), "PAG-6001 2/3")

    fechamento = fechar(recebiveis=parcelas, lancamentos=[credito], lojas=LOJAS, corte=CORTE)

    # A 3/3 vence em 04/12: é a vencer e fica fora dos grupos.
    assert len(fechamento.grupos) == 2
    assert grupo_da_parcela(fechamento, 2).caiu_centavos == 177300
    primeira = grupo_da_parcela(fechamento, 1)
    assert primeira.creditos == []
    assert primeira.nao_caiu_centavos == 177300


def test_nsu_sem_parcela_com_uma_candidata_casa():
    # A 1/3 já tem crédito. A 2/3 é a única vencida sem crédito.
    parcelas = [
        parcela_6001(1, date(2026, 10, 6)),
        parcela_6001(2, date(2026, 11, 6)),
    ]
    credito_1 = credito_6001("ext_a", em_sao_paulo(10, 6), "PAG-6001 1/3")
    credito_sem_parcela = credito_6001("ext_b", em_sao_paulo(11, 6), "PAG-6001")

    fechamento = fechar(
        recebiveis=parcelas, lancamentos=[credito_1, credito_sem_parcela], lojas=LOJAS, corte=CORTE
    )

    assert len(fechamento.grupos) == 2
    assert [c.id for c in grupo_da_parcela(fechamento, 1).creditos] == ["ext_a"]
    assert [c.id for c in grupo_da_parcela(fechamento, 2).creditos] == ["ext_b"]
    assert fechamento.pendencias == []


def test_nsu_sem_parcela_com_varias_candidatas_gera_grupo_ambiguo():
    # A 1/3 e a 2/3 venceram sem crédito, e o crédito não diz qual paga.
    parcelas = [
        parcela_6001(1, date(2026, 10, 6)),
        parcela_6001(2, date(2026, 11, 6)),
    ]
    credito = credito_6001("ext_a", em_sao_paulo(11, 6), "PAG-6001")

    fechamento = fechar(recebiveis=parcelas, lancamentos=[credito], lojas=LOJAS, corte=CORTE)

    [grupo] = fechamento.grupos
    assert {r.id for r in grupo.recebiveis} == {"rec_6001_1", "rec_6001_2"}
    assert grupo.esperado_centavos == 354600
    assert grupo.caiu_centavos == 177300
    assert grupo.nao_caiu_centavos == 177300


def test_nsu_conhecido_sem_parcela_vencida_vira_pendencia_ligada_a_venda():
    # A 1/3 já caiu. A 2/3 só vence em 04/12, e um crédito sem "n/m" chega em 09/11.
    parcelas = [
        parcela_6001(1, date(2026, 11, 6)),
        parcela_6001(2, date(2026, 12, 4)),
    ]
    credito_1 = credito_6001("ext_a", em_sao_paulo(11, 6), "PAG-6001 1/3")
    adiantado = credito_6001("ext_b", em_sao_paulo(11, 9), "PAG-6001")

    fechamento = fechar(recebiveis=parcelas, lancamentos=[credito_1, adiantado], lojas=LOJAS, corte=CORTE)

    # Os totais não mudam: a 2/3 continua a vencer.
    [grupo] = fechamento.grupos
    assert [r.id for r in grupo.recebiveis] == ["rec_6001_1"]
    assert grupo.caiu_centavos == 177300
    [pendencia] = fechamento.pendencias
    assert pendencia.motivo == Motivo.PODE_SER_ANTECIPACAO
    assert pendencia.severidade == Severidade.PARA_CONFERIR
    assert pendencia.valor_centavos == 177300
    assert pendencia.lancamento.id == "ext_b"


def test_data_na_descricao_nao_e_parcela():
    # "06/11" é a data, não a parcela 6 de 11: a venda tem 3 parcelas.
    parcelas = [parcela_6001(1, date(2026, 11, 6)), parcela_6001(2, date(2026, 12, 4))]
    credito = credito_6001("ext_08", em_sao_paulo(11, 6), "PAG-6001 ref 06/11")

    fechamento = fechar(recebiveis=parcelas, lancamentos=[credito], lojas=LOJAS, corte=CORTE)

    assert grupo_da_parcela(fechamento, 1).caiu_centavos == 177300
    assert fechamento.pendencias == []


def test_parcela_indicada_inexistente_fica_ligada_a_venda():
    # O arquivo da adquirente só tem a 1/3 e a 2/3, e cai um crédito da 3/3.
    parcelas = [parcela_6001(1, date(2026, 11, 6)), parcela_6001(2, date(2026, 12, 4))]
    credito_1 = credito_6001("ext_08", em_sao_paulo(11, 6), "PAG-6001 1/3")
    terceira = credito_6001("ext_c", em_sao_paulo(11, 9), "PAG-6001 3/3")

    fechamento = fechar(recebiveis=parcelas, lancamentos=[credito_1, terceira], lojas=LOJAS, corte=CORTE)

    [pendencia] = fechamento.pendencias
    assert pendencia.motivo == Motivo.PODE_SER_ANTECIPACAO
    assert pendencia.lancamento.id == "ext_c"
