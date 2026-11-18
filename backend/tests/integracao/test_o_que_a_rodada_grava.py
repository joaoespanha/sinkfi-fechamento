"""O que a rodada grava (ADR 0006): cópia do que usou, versão da regra e corte."""

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.rodadas import rodar_fechamento
from sinkfi.tipos import ItemRodada, Rodada

from tests.construtores import CORTE
from tests.integracao.cenarios import (
    MARINA,
    dados_com_credito_a_mais,
    dados_com_mesmo_id_na_pagseguro,
    dados_com_recebivel_cancelado,
    preparar_marina,
)


def item_com_recebivel(sessao: Session, rodada: Rodada, recebivel_id: str) -> ItemRodada:
    [item] = [
        i
        for i in repositorios.itens_da_rodada(sessao, rodada.id)
        if recebivel_id in {r.id for r in i.recebiveis}
    ]
    return item


def test_item_guarda_copia_dos_recebiveis_e_creditos(sessao: Session):
    preparar_marina(sessao)
    rodada = rodar_fechamento(sessao, MARINA, CORTE)

    item = item_com_recebivel(sessao, rodada, "rec_1002")

    assert item.recebiveis[0].liquido_centavos == 87714
    assert [c.id for c in item.creditos] == ["ext_03"]
    assert item.creditos[0].valor_centavos == 87714


def test_rodada_antiga_nao_muda_quando_recebivel_e_cancelado(sessao: Session, tmp_path: Path):
    preparar_marina(sessao)
    antiga = rodar_fechamento(sessao, MARINA, CORTE)

    ingerir(sessao, MARINA, dados_com_recebivel_cancelado(tmp_path, "rec_1002"))
    nova = rodar_fechamento(sessao, MARINA, CORTE)

    assert nova.id != antiga.id
    assert item_com_recebivel(sessao, antiga, "rec_1002").recebiveis[0].status == "open"


def test_versao_nova_da_regra_cria_rodada_nova_com_mesma_entrada(sessao: Session):
    preparar_marina(sessao)
    v1 = rodar_fechamento(sessao, MARINA, CORTE, versao="1")
    v2 = rodar_fechamento(sessao, MARINA, CORTE, versao="2")

    assert v2.id != v1.id
    assert (v1.versao_regra, v2.versao_regra) == ("1", "2")


def test_busca_rodadas_por_recebivel(sessao: Session, tmp_path: Path):
    preparar_marina(sessao)
    anterior = rodar_fechamento(sessao, MARINA, CORTE)
    ingerir(sessao, MARINA, dados_com_credito_a_mais(tmp_path))
    nova = rodar_fechamento(sessao, MARINA, CORTE)

    rodadas = repositorios.rodadas_com_recebivel(sessao, MARINA, "stone", "rec_1002")

    assert [r.id for r in rodadas] == [nova.id, anterior.id]


def test_busca_rodadas_pelo_recebivel_da_adquirente(sessao: Session, tmp_path: Path):
    # O `rec_1002` da PagSeguro só entra na segunda rodada; o da Stone está nas duas.
    preparar_marina(sessao)
    so_stone = rodar_fechamento(sessao, MARINA, CORTE)
    ingerir(sessao, MARINA, dados_com_mesmo_id_na_pagseguro(tmp_path))
    com_as_duas = rodar_fechamento(sessao, MARINA, CORTE)

    da_pagseguro = repositorios.rodadas_com_recebivel(sessao, MARINA, "pagseguro", "rec_1002")
    da_stone = repositorios.rodadas_com_recebivel(sessao, MARINA, "stone", "rec_1002")

    assert [r.id for r in da_pagseguro] == [com_as_duas.id]
    assert [r.id for r in da_stone] == [com_as_duas.id, so_stone.id]


def test_rodada_guarda_o_corte_usado(sessao: Session):
    preparar_marina(sessao)
    rodar_fechamento(sessao, MARINA, CORTE)

    [rodada] = repositorios.rodadas_do_cliente(sessao, MARINA)

    assert rodada.corte == CORTE
    assert rodada.data_fechamento == date(2026, 11, 10)


def test_rodada_usa_o_status_do_lancamento_do_banco(sessao: Session):
    # O T-4002 está `pending` no extrato: em 17/11 ele ainda não caiu.
    preparar_marina(sessao)
    rodada = rodar_fechamento(sessao, MARINA, datetime(2026, 11, 17, 18, 0, tzinfo=ZoneInfo("America/Sao_Paulo")))

    item = item_com_recebivel(sessao, rodada, "rec_4002")

    assert item.creditos[0].status == "pending"
    assert item.caiu_centavos == 0
    assert item.proximo_fechamento_centavos == 500000
