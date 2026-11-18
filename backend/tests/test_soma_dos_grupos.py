"""Invariantes contra os CSVs reais (ADR 0002)."""

from datetime import datetime
from pathlib import Path

import pytest

from fechamento import fechar
from sinkfi.ingestao import csv

from tests.construtores import CORTE, SAO_PAULO

DADOS = Path(__file__).resolve().parents[2] / "dados"
CORTE_SEGUINTE = datetime(2026, 11, 17, 18, 0, tzinfo=SAO_PAULO)


def test_soma_dos_grupos_fecha_com_o_esperado():
    recebiveis, lancamentos, lojas = csv.ler(DADOS)

    fechamento = fechar(recebiveis=recebiveis, lancamentos=lancamentos, lojas=lojas, corte=CORTE)

    grupos = fechamento.grupos
    assert sum(g.esperado_centavos for g in grupos) == 3941322
    assert sum(g.caiu_centavos for g in grupos) == 2606589
    assert sum(g.nao_caiu_centavos for g in grupos) == 770733
    assert sum(g.proximo_fechamento_centavos for g in grupos) == 564000


@pytest.mark.parametrize("corte", [CORTE, CORTE_SEGUINTE], ids=["10/11", "17/11"])
def test_cada_grupo_fecha_com_o_seu_esperado(corte):
    recebiveis, lancamentos, lojas = csv.ler(DADOS)

    fechamento = fechar(recebiveis=recebiveis, lancamentos=lancamentos, lojas=lojas, corte=corte)

    for g in fechamento.grupos:
        assert g.esperado_centavos == g.caiu_centavos + g.nao_caiu_centavos + g.proximo_fechamento_centavos


def test_credito_pending_continua_no_proximo_fechamento_na_semana_seguinte():
    # Em 17/11 o T-4002 continua `pending` no extrato: não caiu, mesmo uma semana depois.
    recebiveis, lancamentos, lojas = csv.ler(DADOS)

    fechamento = fechar(recebiveis=recebiveis, lancamentos=lancamentos, lojas=lojas, corte=CORTE_SEGUINTE)

    [grupo] = [g for g in fechamento.grupos if any(r.id == "rec_4002" for r in g.recebiveis)]
    assert grupo.caiu_centavos == 0
    assert grupo.proximo_fechamento_centavos == 500000
