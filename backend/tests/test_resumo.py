"""Resumo e trava (ADR 0003): (pendências, limite) -> resumo."""

from fechamento import Motivo, Pendencia, Recomendacao, Severidade, resumo


def falta(valor_centavos: int, motivo: Motivo = Motivo.NAO_CAIU) -> Pendencia:
    return Pendencia(Severidade.FALTA_DE_VERDADE, motivo, valor_centavos)


def para_conferir(valor_centavos: int) -> Pendencia:
    return Pendencia(Severidade.PARA_CONFERIR, Motivo.ENTRADA_SEM_RECEBIVEL, valor_centavos)


def test_resumo_sem_falta_de_verdade_diz_pode_fechar():
    r = resumo([para_conferir(4433)])

    assert r.recomendacao == Recomendacao.PODE_FECHAR
    assert r.falta_de_verdade_centavos == 0
    assert r.itens_falta_de_verdade == 0
    assert r.itens_para_conferir == 1


def test_resumo_com_falta_de_verdade_mostra_total_e_quantidade():
    r = resumo([falta(477500, Motivo.CAIU_EM_PARTE), falta(4433)])

    assert r.recomendacao == Recomendacao.FALTAM
    assert r.falta_de_verdade_centavos == 481933
    assert r.itens_falta_de_verdade == 2


def test_trava_desligada_por_padrao_nunca_trava():
    r = resumo([falta(10_000_000)])

    assert r.recomendacao == Recomendacao.FALTAM


def test_trava_soma_faltas_sem_compensar_sobra():
    # 4.775,00 que não caíram do rec_7001 e 3.152,00 que caíram da venda cancelada T-2009.
    pendencias = [falta(477500, Motivo.CAIU_EM_PARTE), falta(315200, Motivo.VENDA_CANCELADA)]

    r = resumo(pendencias, limite_trava_centavos=200000)

    assert r.falta_de_verdade_centavos == 792700
    assert r.recomendacao == Recomendacao.NAO_FECHE


def test_trava_ignora_itens_para_conferir():
    r = resumo([falta(100000), para_conferir(500000)], limite_trava_centavos=200000)

    assert r.recomendacao == Recomendacao.PODE_FECHAR
    assert r.falta_de_verdade_centavos == 100000
    assert r.itens_para_conferir == 1


def test_falta_abaixo_do_limite_resumo_pode_fechar():
    r = resumo([falta(4433)], limite_trava_centavos=200000)

    assert r.recomendacao == Recomendacao.PODE_FECHAR
    assert r.falta_de_verdade_centavos == 4433
    assert r.itens_falta_de_verdade == 1


def test_falta_acima_do_limite_resumo_nao_feche():
    r = resumo([falta(477500, Motivo.CAIU_EM_PARTE)], limite_trava_centavos=200000)

    assert r.recomendacao == Recomendacao.NAO_FECHE
