"""Cenários dos testes de integração: a Marina com os CSVs de `dados/` e os lotes reenviados.

O cenário é montado pela `ingerir`, nunca com SQL direto.
"""

import shutil
from datetime import time
from pathlib import Path

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir

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
    _copiar_dados(pasta)
    with (pasta / "extrato.csv").open("a", encoding="utf-8") as extrato:
        extrato.write(
            "ext_99,T-NOVO,,2026-11-10T11:00:00-03:00,12345,STONE PAGAMENTOS,"
            "16501555000100,STN-9999,confirmed,settlement\n"
        )
    return pasta


def dados_com_recebivel_cancelado(pasta: Path, recebivel_id: str) -> Path:
    """O lote reenviado: os mesmos CSVs, com um recebível que a adquirente cancelou."""
    _copiar_dados(pasta)
    arquivo = pasta / "recebiveis.csv"
    linhas = arquivo.read_text(encoding="utf-8").splitlines(keepends=True)
    arquivo.write_text(
        "".join(
            l.replace(",open\n", ",cancelled\n") if l.startswith(f"{recebivel_id},") else l
            for l in linhas
        ),
        encoding="utf-8",
    )
    return pasta


def _copiar_dados(pasta: Path) -> None:
    for arquivo in DADOS.glob("*.csv"):
        shutil.copy(arquivo, pasta)
