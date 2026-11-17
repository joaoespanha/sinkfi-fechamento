"""Rodada imutável (ADR 0004): a mesma entrada não gera outra rodada."""

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


def test_mesma_entrada_devolve_a_rodada_que_ja_existe(sessao: Session):
    preparar_marina(sessao)

    primeira = rodar_fechamento(sessao, MARINA, CORTE)
    segunda = rodar_fechamento(sessao, MARINA, CORTE)

    assert segunda.id == primeira.id
