"""Lê os CSVs de dados/ e devolve os tipos de entrada da regra."""

from pathlib import Path

from fechamento.tipos import Lancamento, Loja, Recebivel


def ler(pasta: Path) -> tuple[list[Recebivel], list[Lancamento], list[Loja]]:
    raise NotImplementedError
