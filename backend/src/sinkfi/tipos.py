"""Tipos da casca que atravessam repositórios e serviços. Nenhum deles é ORM."""

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum

from fechamento import Lancamento, Loja, Motivo, Recebivel, Resumo, Severidade


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
    criada_em: datetime


@dataclass(frozen=True)
class ItemRodada:
    """Um grupo de recebíveis ou um crédito que não paga nenhum recebível esperado.

    O item de crédito não tem recebíveis nem valores de grupo. Severidade, motivo e
    valor existem quando o item é uma pendência.
    """

    recebiveis: list[Recebivel]
    creditos: list[Lancamento]
    esperado_centavos: int | None = None
    caiu_centavos: int | None = None
    nao_caiu_centavos: int | None = None
    proximo_fechamento_centavos: int | None = None
    severidade: Severidade | None = None
    motivo: Motivo | None = None
    pendencia_centavos: int | None = None


@dataclass(frozen=True)
class ConfigFechamento:
    # Como `isoweekday`: 1 = segunda, 7 = domingo.
    dia_fechamento: int
    hora_corte: time
    fuso: str


class Papel(StrEnum):
    LOJISTA = "lojista"
    SUPORTE = "suporte"


@dataclass(frozen=True)
class Usuario:
    """Sem a senha: o hash só sai do repositório para a conferência do login."""

    id: int
    email: str
    papel: Papel
    cliente_id: str | None
    ativo: bool


@dataclass(frozen=True)
class MudancaLimite:
    """None em `de`/`para` = trava desligada (ADR 0003)."""

    quem: str
    em: datetime
    de_centavos: int | None
    para_centavos: int | None


@dataclass(frozen=True)
class Termino:
    """Um "Terminei": a rodada que a lojista viu, com o limite e o resumo daquele momento."""

    quem: str
    em: datetime
    rodada_id: int
    limite_trava_centavos: int | None
    resumo: Resumo
