"""A ingestão de um cliente não toca no dado de outro (ADR 0009).

Os IDs vêm de fora (adquirente, banco, cadastro do cliente) e podem se repetir entre clientes.
"""

import shutil
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.tipos import Entrada

from tests.integracao.cenarios import DADOS, MARINA, OUTRO, preparar_marina, preparar_outro_cliente


def test_outro_cliente_com_os_mesmos_ids_nao_muda_a_entrada_da_marina(sessao: Session):
    preparar_marina(sessao)
    antes = _sem_ordem(repositorios.entrada_do_cliente(sessao, MARINA))
    preparar_outro_cliente(sessao)

    ingerir(sessao, OUTRO, DADOS)

    assert _sem_ordem(repositorios.entrada_do_cliente(sessao, MARINA)) == antes
    assert _sem_ordem(repositorios.entrada_do_cliente(sessao, OUTRO)) == antes


def test_recebivel_que_aponta_para_loja_de_outro_cliente_recusa_a_ingestao(sessao: Session, tmp_path: Path):
    preparar_marina(sessao)
    preparar_outro_cliente(sessao)
    # O outro cliente manda os recebíveis da Marina sem cadastrar as lojas deles.
    shutil.copy(DADOS / "recebiveis.csv", tmp_path)
    shutil.copy(DADOS / "extrato.csv", tmp_path)
    (tmp_path / "lojas.csv").write_text("id,name,document,acquirer\n", encoding="utf-8")

    with pytest.raises(IntegrityError, match="recebiveis_loja_fkey"):
        ingerir(sessao, OUTRO, tmp_path)


def _sem_ordem(entrada: Entrada) -> tuple[frozenset, ...]:
    """A consulta não ordena as linhas, e o Postgres não garante a ordem."""
    return (frozenset(entrada.recebiveis), frozenset(entrada.lancamentos), frozenset(entrada.lojas))
