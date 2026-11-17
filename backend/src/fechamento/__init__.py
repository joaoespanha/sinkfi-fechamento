"""Regra pura do fechamento: sem banco, sem rede, sem relógio."""

from fechamento.fechar import VERSAO_DA_REGRA, fechar
from fechamento.resumo import resumo
from fechamento.tipos import (
    Fechamento,
    GrupoDeRecebiveis,
    Lancamento,
    Loja,
    Motivo,
    Pendencia,
    Recebivel,
    Recomendacao,
    Resumo,
    Severidade,
)

__all__ = [
    "Fechamento",
    "GrupoDeRecebiveis",
    "Lancamento",
    "Loja",
    "Motivo",
    "Pendencia",
    "Recebivel",
    "Recomendacao",
    "Resumo",
    "Severidade",
    "VERSAO_DA_REGRA",
    "fechar",
    "resumo",
]
