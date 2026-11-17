"""Regra pura do fechamento: sem banco, sem rede, sem relógio."""

from fechamento.fechar import fechar
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
    "fechar",
    "resumo",
]
