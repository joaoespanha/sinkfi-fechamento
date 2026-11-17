"""Tipos da casca que atravessam repositórios e serviços. Nenhum deles é ORM."""

from dataclasses import dataclass
from datetime import date, datetime

from fechamento import Lancamento, Loja, Recebivel


@dataclass(frozen=True)
class Entrada:
    """O que a regra recebe de um cliente, lido do banco."""

    recebiveis: list[Recebivel]
    lancamentos: list[Lancamento]
    lojas: list[Loja]


@dataclass(frozen=True)
class Rodada:
    id: int
    cliente_id: str
    data_fechamento: date
    corte: datetime
    versao_regra: str
    hash_entrada: str
