"""Regra pura do fechamento: sem banco, sem rede, sem relógio."""

from fechamento.fechar import fechar
from fechamento.tipos import Fechamento, GrupoDeRecebiveis, Lancamento, Loja, Recebivel

__all__ = ["Fechamento", "GrupoDeRecebiveis", "Lancamento", "Loja", "Recebivel", "fechar"]
