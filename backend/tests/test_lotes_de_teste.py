"""Os lotes de dados-teste/ contra a regra: os números de dados-teste/LEIA.md."""

from datetime import datetime
from pathlib import Path

import pytest

from fechamento import Severidade, fechar
from sinkfi.ingestao import csv

from tests.construtores import SAO_PAULO

DADOS_TESTE = Path(__file__).resolve().parents[2] / "dados-teste"


def corte(dia: int) -> datetime:
    return datetime(2026, 11, dia, 18, 0, tzinfo=SAO_PAULO)


@pytest.mark.parametrize(
    ("lote", "dia", "falta_centavos", "faltas", "para_conferir"),
    [
        ("lote1", 3, 230000, 1, 0),
        ("lote1", 10, 1315933, 6, 2),
        ("lote1", 17, 1778233, 10, 4),
        ("lote2", 3, 0, 0, 0),
        ("lote2", 10, 1085933, 5, 2),
        ("lote2", 17, 1576233, 9, 4),
    ],
)
def test_numeros_do_fechamento(lote, dia, falta_centavos, faltas, para_conferir):
    recebiveis, lancamentos, lojas = csv.ler(DADOS_TESTE / lote)

    fechamento = fechar(recebiveis=recebiveis, lancamentos=lancamentos, lojas=lojas, corte=corte(dia))

    falta = [p for p in fechamento.pendencias if p.severidade == Severidade.FALTA_DE_VERDADE]
    conferir = [p for p in fechamento.pendencias if p.severidade == Severidade.PARA_CONFERIR]
    assert (sum(p.valor_centavos for p in falta), len(falta), len(conferir)) == (
        falta_centavos,
        faltas,
        para_conferir,
    )


def test_lote1_em_03_11_so_falta_o_stn_3103():
    recebiveis, lancamentos, lojas = csv.ler(DADOS_TESTE / "lote1")

    fechamento = fechar(recebiveis=recebiveis, lancamentos=lancamentos, lojas=lojas, corte=corte(3))

    [pendencia] = fechamento.pendencias
    assert [r.nsu for r in pendencia.grupo.recebiveis] == ["STN-3103"]


@pytest.mark.parametrize("lote", ["lote1", "lote2"])
def test_venda_cancelada_de_14_11_nao_entra_no_fechamento_de_10_11(lote):
    recebiveis, lancamentos, lojas = csv.ler(DADOS_TESTE / lote)

    fechamento = fechar(recebiveis=recebiveis, lancamentos=lancamentos, lojas=lojas, corte=corte(10))

    assert "ext_53" not in {p.lancamento.id for p in fechamento.pendencias if p.lancamento}
