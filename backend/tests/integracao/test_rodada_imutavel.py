"""Rodada imutável (ADR 0004): a mesma entrada não gera outra rodada."""

import shutil
from datetime import time
from pathlib import Path

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.rodadas import rodar_fechamento

from tests.construtores import CORTE

DADOS = Path(__file__).resolve().parents[3] / "dados"
MARINA = "cli_marina"


def preparar_marina(sessao: Session) -> None:
    repositorios.criar_cliente(
        sessao,
        id=MARINA,
        nome="Marina",
        dia_fechamento=1,
        hora_corte=time(18, 0),
        fuso="America/Sao_Paulo",
    )
    ingerir(sessao, MARINA, DADOS)


def dados_com_credito_a_mais(pasta: Path) -> Path:
    """O lote reenviado: os mesmos CSVs, com um crédito novo no extrato antes do corte."""
    for arquivo in DADOS.glob("*.csv"):
        shutil.copy(arquivo, pasta)
    with (pasta / "extrato.csv").open("a", encoding="utf-8") as extrato:
        extrato.write(
            "ext_99,T-NOVO,,2026-11-10T11:00:00-03:00,12345,STONE PAGAMENTOS,"
            "16501555000100,STN-9999,confirmed,settlement\n"
        )
    return pasta


def test_mesma_entrada_devolve_a_rodada_que_ja_existe(sessao: Session):
    preparar_marina(sessao)

    primeira = rodar_fechamento(sessao, MARINA, CORTE)
    segunda = rodar_fechamento(sessao, MARINA, CORTE)

    assert segunda.id == primeira.id


def test_entrada_nova_cria_rodada_e_guarda_a_anterior(sessao: Session, tmp_path: Path):
    preparar_marina(sessao)
    anterior = rodar_fechamento(sessao, MARINA, CORTE)

    ingerir(sessao, MARINA, dados_com_credito_a_mais(tmp_path))
    nova = rodar_fechamento(sessao, MARINA, CORTE)

    assert nova.id != anterior.id
    assert [r.id for r in repositorios.rodadas_do_cliente(sessao, MARINA)] == [nova.id, anterior.id]
