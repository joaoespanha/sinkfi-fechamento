"""Cenários dos testes de integração: a Marina com os CSVs de `dados/` e os lotes reenviados.

O cenário é montado pela `ingerir`, nunca com SQL direto.
"""

import shutil
from datetime import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sinkfi import usuarios
from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.tipos import Papel

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


SENHA = "senha-de-teste"
LOJISTA_MARINA = "marina@sinkfi.test"
SUPORTE = "suporte@sinkfi.test"
OUTRO = "cli_outro"
LOJISTA_OUTRO = "outro@sinkfi.test"


def criar_lojista(sessao: Session, email: str, cliente_id: str) -> None:
    usuarios.criar_usuario(sessao, email=email, senha=SENHA, papel=Papel.LOJISTA, cliente_id=cliente_id)


def criar_suporte(sessao: Session, email: str = SUPORTE) -> None:
    usuarios.criar_usuario(sessao, email=email, senha=SENHA, papel=Papel.SUPORTE)


def preparar_outro_cliente(sessao: Session) -> None:
    """Um segundo cliente, sem dados, com a lojista dele."""
    repositorios.criar_cliente(
        sessao,
        id=OUTRO,
        nome="Outro",
        dia_fechamento=1,
        hora_corte=time(18, 0),
        fuso="America/Sao_Paulo",
    )
    criar_lojista(sessao, LOJISTA_OUTRO, OUTRO)


def entrar(http: TestClient, email: str, senha: str = SENHA) -> None:
    """Login de verdade: o cookie fica no TestClient para as próximas requisições."""
    resposta = http.post("/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 204, resposta.text
