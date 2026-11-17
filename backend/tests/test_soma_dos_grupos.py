"""Invariante contra os CSVs reais de 10/11 (ADR 0002)."""

from pathlib import Path

from fechamento import csv, fechar

from tests.construtores import CORTE

DADOS = Path(__file__).resolve().parents[2] / "dados"


def test_soma_dos_grupos_fecha_com_o_esperado():
    recebiveis, lancamentos, lojas = csv.ler(DADOS)

    fechamento = fechar(recebiveis=recebiveis, lancamentos=lancamentos, lojas=lojas, corte=CORTE)

    grupos = fechamento.grupos
    assert sum(g.esperado_centavos for g in grupos) == 3941322
    assert sum(g.caiu_centavos for g in grupos) == 2606589
    assert sum(g.nao_caiu_centavos for g in grupos) == 770733
    assert sum(g.proximo_fechamento_centavos for g in grupos) == 564000
