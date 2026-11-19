"""O bruto e a taxa de cada venda chegam à rodada: a tela mostra de onde vem o esperado."""

from pathlib import Path

from sinkfi.ingestao.csv import ler

DADOS = Path(__file__).resolve().parents[2] / "dados"


def test_leitura_traz_o_bruto_o_mdr_e_a_antecipacao():
    recebiveis, _, _ = ler(DADOS)
    por_id = {r.id: r for r in recebiveis}

    assert (por_id["rec_4812"].bruto_centavos, por_id["rec_4812"].mdr_centavos) == (481200, 2200)
    assert por_id["rec_8002"].antecipacao_centavos == 4250


def test_bruto_menos_taxas_e_o_liquido_nos_dados_do_desafio():
    recebiveis, _, _ = ler(DADOS)

    for r in recebiveis:
        assert r.bruto_centavos - r.mdr_centavos - r.antecipacao_centavos == r.liquido_centavos, r.id
