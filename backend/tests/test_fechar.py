"""Casamento e corte (ADR 0001), grupos (ADR 0002) e classificação."""

from datetime import date, datetime

from fechamento import Motivo, Severidade, fechar

from tests.construtores import (
    CORTE,
    LOJAS,
    PAGSEGURO,
    UTC,
    em_sao_paulo,
    lancamento,
    recebivel,
)

# Casamento e corte (ADR 0001)


def test_credito_depois_do_corte_vai_para_proximo_fechamento():
    rec_7002 = recebivel(
        "rec_7002",
        adquirente="pagseguro",
        loja_id="loja_savassi",
        liquidacao_prevista=date(2026, 11, 10),
        liquido_centavos=64000,
        nsu="PAG-7002",
    )
    # 21:40Z é 18:40 em São Paulo: caiu 40 minutos depois do corte.
    t_7002 = lancamento(
        "ext_13",
        transacao_id="T-7002",
        lancado_em=datetime(2026, 11, 10, 21, 40, tzinfo=UTC),
        valor_centavos=64000,
        documento_contraparte=PAGSEGURO,
        descricao="PAG-7002",
    )

    fechamento = fechar(recebiveis=[rec_7002], lancamentos=[t_7002], lojas=LOJAS, corte=CORTE)

    [grupo] = fechamento.grupos
    assert grupo.esperado_centavos == 64000
    assert grupo.proximo_fechamento_centavos == 64000
    assert grupo.caiu_centavos == 0
    assert grupo.nao_caiu_centavos == 0
    assert fechamento.pendencias == []


def test_duplicata_nao_vira_pendencia():
    rec_1001 = recebivel(
        "rec_1001",
        liquidacao_prevista=date(2026, 11, 5),
        liquido_centavos=147750,
        nsu="STN-1001",
    )
    # O extrato traz o T-1001 duas vezes, com 7 segundos de diferença.
    ext_01 = lancamento(
        "ext_01",
        transacao_id="T-1001",
        lancado_em=em_sao_paulo(11, 5, 14, 2, 11),
        valor_centavos=147750,
        descricao="STN-1001",
    )
    ext_02 = lancamento(
        "ext_02",
        transacao_id="T-1001",
        lancado_em=em_sao_paulo(11, 5, 14, 2, 18),
        valor_centavos=147750,
        descricao="STN-1001",
    )

    fechamento = fechar(recebiveis=[rec_1001], lancamentos=[ext_01, ext_02], lojas=LOJAS, corte=CORTE)

    [grupo] = fechamento.grupos
    assert grupo.esperado_centavos == 147750
    assert grupo.caiu_centavos == 147750
    assert grupo.nao_caiu_centavos == 0
    assert grupo.proximo_fechamento_centavos == 0
    assert fechamento.pendencias == []


def test_normalizacao_tira_tarifa_e_transferencia_da_titular():
    # Tarifa da conta e transferência da própria titular não são crédito (GLOSSARY.md).
    t_fee = lancamento(
        "ext_17",
        transacao_id="T-FEE",
        lancado_em=em_sao_paulo(11, 10, 23, 59),
        valor_centavos=350,
        documento_contraparte="00416968000100",
        descricao="TARIFA PACOTE",
        tipo="fee",
    )
    t_int = lancamento(
        "ext_18",
        transacao_id="T-INT",
        lancado_em=em_sao_paulo(11, 10, 9, 0),
        valor_centavos=500000,
        documento_contraparte="10493827000160",
        descricao="TRANSFERENCIA MESMA TITULARIDADE",
        tipo="internal_transfer",
    )

    fechamento = fechar(recebiveis=[], lancamentos=[t_fee, t_int], lojas=LOJAS, corte=CORTE)

    assert fechamento.pendencias == []


# Grupos (ADR 0002)


def test_casamento_usa_a_adquirente_do_recebivel():
    rec_1001 = recebivel(
        "rec_1001",
        liquidacao_prevista=date(2026, 11, 5),
        liquido_centavos=147750,
        nsu="STN-1001",
    )
    ext_01 = lancamento(
        "ext_01",
        transacao_id="T-1001",
        lancado_em=em_sao_paulo(11, 5, 14, 2, 11),
        valor_centavos=147750,
        descricao="STN-1001",
    )
    # T-XREF: Pix de um terceiro que cita o NSU da Stone. Não vem da Stone.
    ext_20 = lancamento(
        "ext_20",
        transacao_id="T-XREF",
        lancado_em=em_sao_paulo(11, 9, 17, 5, 41),
        valor_centavos=147750,
        documento_contraparte="11111111000111",
        descricao="STN-1001",
        tipo="pix_in",
    )

    fechamento = fechar(recebiveis=[rec_1001], lancamentos=[ext_01, ext_20], lojas=LOJAS, corte=CORTE)

    [grupo] = fechamento.grupos
    assert [c.id for c in grupo.creditos] == ["ext_01"]
    assert grupo.caiu_centavos == 147750


def test_empate_na_chave_fraca_gera_um_grupo_com_os_dois_recebiveis():
    # rec_3001 e rec_3002: mesma loja, mesma adquirente, mesmo líquido, mesma data.
    rec_3001 = recebivel(
        "rec_3001",
        liquidacao_prevista=date(2026, 11, 9),
        liquido_centavos=210000,
        nsu="STN-3001",
    )
    rec_3002 = recebivel(
        "rec_3002",
        liquidacao_prevista=date(2026, 11, 9),
        liquido_centavos=210000,
        nsu="STN-3002",
    )
    # T-3000: um crédito de 2.100,00 sem NSU.
    t_3000 = lancamento(
        "ext_05",
        transacao_id="T-3000",
        lancado_em=em_sao_paulo(11, 9, 13, 15),
        valor_centavos=210000,
        descricao="stone",
    )

    fechamento = fechar(recebiveis=[rec_3001, rec_3002], lancamentos=[t_3000], lojas=LOJAS, corte=CORTE)

    [grupo] = fechamento.grupos
    assert {r.id for r in grupo.recebiveis} == {"rec_3001", "rec_3002"}
    assert [c.id for c in grupo.creditos] == ["ext_05"]
    assert grupo.esperado_centavos == 420000
    assert grupo.caiu_centavos == 210000
    assert grupo.nao_caiu_centavos == 210000
    assert not grupo.entre_lojas
    [pendencia] = fechamento.pendencias
    assert pendencia.motivo == Motivo.GRUPO_NAO_FECHA
    assert pendencia.severidade == Severidade.FALTA_DE_VERDADE
    assert pendencia.valor_centavos == 210000


def test_empate_entre_lojas_vai_para_a_linha_entre_lojas():
    # Caso construído: os CSVs não têm a mesma adquirente em duas lojas.
    # A Savassi recebe pela Stone aqui, e a adquirente vem do recebível.
    rec_centro = recebivel(
        "rec_centro",
        loja_id="loja_centro",
        liquidacao_prevista=date(2026, 11, 9),
        liquido_centavos=50000,
        nsu="STN-9001",
    )
    rec_savassi = recebivel(
        "rec_savassi",
        loja_id="loja_savassi",
        liquidacao_prevista=date(2026, 11, 9),
        liquido_centavos=50000,
        nsu="STN-9002",
    )
    credito = lancamento(
        "ext_x",
        transacao_id="T-9000",
        lancado_em=em_sao_paulo(11, 9),
        valor_centavos=50000,
        descricao="stone",
    )

    fechamento = fechar(recebiveis=[rec_centro, rec_savassi], lancamentos=[credito], lojas=LOJAS, corte=CORTE)

    [grupo] = fechamento.grupos
    assert {r.id for r in grupo.recebiveis} == {"rec_centro", "rec_savassi"}
    assert grupo.entre_lojas


# Classificação


def test_venda_cancelada_com_credito_e_falta_de_verdade():
    rec_2009 = recebivel(
        "rec_2009",
        adquirente="pagseguro",
        loja_id="loja_savassi",
        liquidacao_prevista=date(2026, 11, 6),
        liquido_centavos=315200,
        nsu="PAG-2009",
        status="cancelled",
    )
    t_2009 = lancamento(
        "ext_07",
        transacao_id="T-2009",
        lancado_em=em_sao_paulo(11, 9, 17, 44, 2),
        valor_centavos=315200,
        documento_contraparte=PAGSEGURO,
        descricao="PAG-2009",
    )

    fechamento = fechar(recebiveis=[rec_2009], lancamentos=[t_2009], lojas=LOJAS, corte=CORTE)

    # Venda cancelada não é esperada: fica fora dos grupos.
    assert fechamento.grupos == []
    [pendencia] = fechamento.pendencias
    assert pendencia.motivo == Motivo.VENDA_CANCELADA
    assert pendencia.severidade == Severidade.FALTA_DE_VERDADE
    assert pendencia.valor_centavos == 315200
    assert pendencia.lancamento.id == "ext_07"


def test_entrada_sem_recebivel_e_para_conferir():
    rec_1003 = recebivel(
        "rec_1003",
        liquidacao_prevista=date(2026, 11, 9),
        liquido_centavos=4433,
        nsu="STN-1003",
    )
    # T-TRAP: Pix de pessoa física com o mesmo valor do rec_1003.
    t_trap = lancamento(
        "ext_19",
        transacao_id="T-TRAP",
        lancado_em=em_sao_paulo(11, 9, 16, 40),
        valor_centavos=4433,
        documento_contraparte="99999999000199",
        descricao="4433",
        tipo="pix_in",
    )

    fechamento = fechar(recebiveis=[rec_1003], lancamentos=[t_trap], lojas=LOJAS, corte=CORTE)

    [grupo] = fechamento.grupos
    assert grupo.nao_caiu_centavos == 4433
    pendencias = {(p.motivo, p.severidade, p.valor_centavos) for p in fechamento.pendencias}
    assert pendencias == {
        (Motivo.NAO_CAIU, Severidade.FALTA_DE_VERDADE, 4433),
        (Motivo.ENTRADA_SEM_RECEBIVEL, Severidade.PARA_CONFERIR, 4433),
    }


def test_chargeback_e_falta_de_verdade():
    rec_5001 = recebivel(
        "rec_5001",
        adquirente="pagseguro",
        loja_id="loja_savassi",
        liquidacao_prevista=date(2026, 11, 6),
        liquido_centavos=78800,
        nsu="PAG-5001",
    )
    t_5001 = lancamento(
        "ext_09",
        transacao_id="T-5001",
        lancado_em=em_sao_paulo(11, 6, 12, 30),
        valor_centavos=78800,
        documento_contraparte=PAGSEGURO,
        descricao="PAG-5001",
    )
    # O chargeback cai às 19:12, depois do corte, mas desfaz um crédito deste fechamento.
    t_5001r = lancamento(
        "ext_10",
        transacao_id="T-5001R",
        transacao_original_id="T-5001",
        lancado_em=em_sao_paulo(11, 10, 19, 12, 44),
        valor_centavos=78800,
        documento_contraparte=PAGSEGURO,
        descricao="CHARGEBACK T-5001",
        tipo="chargeback",
    )

    fechamento = fechar(recebiveis=[rec_5001], lancamentos=[t_5001, t_5001r], lojas=LOJAS, corte=CORTE)

    [grupo] = fechamento.grupos
    assert grupo.caiu_centavos == 0
    assert grupo.nao_caiu_centavos == 78800
    [pendencia] = fechamento.pendencias
    assert pendencia.motivo == Motivo.CHARGEBACK
    assert pendencia.severidade == Severidade.FALTA_DE_VERDADE
    assert pendencia.valor_centavos == 78800
