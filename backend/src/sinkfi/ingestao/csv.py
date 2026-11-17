"""Lê os CSVs de dados/ e devolve os tipos de entrada da regra.

Só traduz colunas e tipos. Fuso, duplicatas e tarifas ficam para a normalização (ADR 0001).
"""

import csv
from datetime import date, datetime
from pathlib import Path

from fechamento.tipos import Lancamento, Loja, Recebivel


def ler(pasta: Path) -> tuple[list[Recebivel], list[Lancamento], list[Loja]]:
    recebiveis = [_recebivel(linha) for linha in _linhas(pasta / "recebiveis.csv")]
    lancamentos = [_lancamento(linha) for linha in _linhas(pasta / "extrato.csv")]
    lojas = [_loja(linha) for linha in _linhas(pasta / "lojas.csv")]
    return recebiveis, lancamentos, lojas


def _linhas(arquivo: Path) -> list[dict[str, str]]:
    with arquivo.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _recebivel(linha: dict[str, str]) -> Recebivel:
    return Recebivel(
        id=linha["id"],
        loja_id=linha["loja_id"],
        adquirente=linha["acquirer"],
        trilho=linha["rail"],
        vendido_em=date.fromisoformat(linha["sold_at"]),
        liquidacao_prevista=date.fromisoformat(linha["expected_settlement_at"]),
        liquido_centavos=int(linha["net_cents"]),
        nsu=linha["nsu"],
        parcela=int(linha["installment_number"]),
        parcelas=int(linha["installment_count"]),
        status=linha["status"],
    )


def _lancamento(linha: dict[str, str]) -> Lancamento:
    return Lancamento(
        id=linha["id"],
        transacao_id=linha["transaction_id"],
        transacao_original_id=linha["original_transaction_id"] or None,
        lancado_em=datetime.fromisoformat(linha["booked_at"]),
        valor_centavos=int(linha["amount_cents"]),
        documento_contraparte=linha["counterparty_document"],
        descricao=linha["description"],
        tipo=linha["kind"],
    )


def _loja(linha: dict[str, str]) -> Loja:
    return Loja(id=linha["id"], documento=linha["document"], adquirente=linha["acquirer"])
