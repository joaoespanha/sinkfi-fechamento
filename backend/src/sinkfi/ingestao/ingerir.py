"""Grava os CSVs de um cliente no banco, com todas as colunas.

`sinkfi.ingestao.csv` lê só o que a regra usa; aqui nada é descartado, porque a
próxima versão da regra pode precisar de uma coluna que esta não usa.

Na mesma transação do dado, grava o pedido de fechamento (o outbox do ADR 0004):
se o dado entra, o pedido entra; se a transação desfaz, os dois somem.
"""

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from sinkfi.banco import repositorios


def ingerir(sessao: Session, cliente_id: str, pasta: Path) -> None:
    # A rodada trava o mesmo cliente: ela não lê a entrada no meio da gravação.
    repositorios.travar_cliente(sessao, cliente_id)
    repositorios.gravar_lojas(sessao, [_loja(l, cliente_id) for l in _linhas(pasta / "lojas.csv")])
    repositorios.gravar_recebiveis(sessao, [_recebivel(l) for l in _linhas(pasta / "recebiveis.csv")])
    repositorios.gravar_lancamentos(sessao, [_lancamento(l, cliente_id) for l in _linhas(pasta / "extrato.csv")])
    repositorios.gravar_pedido_fechamento(sessao, cliente_id)


def _linhas(arquivo: Path) -> list[dict[str, str]]:
    with arquivo.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _loja(linha: dict[str, str], cliente_id: str) -> dict[str, Any]:
    return {
        "id": linha["id"],
        "cliente_id": cliente_id,
        "nome": linha["name"],
        "documento": linha["document"],
        "adquirente": linha["acquirer"],
    }


def _recebivel(linha: dict[str, str]) -> dict[str, Any]:
    return {
        "id": linha["id"],
        "loja_id": linha["loja_id"],
        "adquirente": linha["acquirer"],
        "trilho": linha["rail"],
        "vendido_em": date.fromisoformat(linha["sold_at"]),
        "liquidacao_prevista": date.fromisoformat(linha["expected_settlement_at"]),
        "bruto_centavos": int(linha["gross_cents"]),
        "mdr_centavos": int(linha["mdr_cents"]),
        "antecipacao_centavos": int(linha["anticipation_cents"]),
        "liquido_centavos": int(linha["net_cents"]),
        "nsu": linha["nsu"],
        "parcela": int(linha["installment_number"]),
        "parcelas": int(linha["installment_count"]),
        "status": linha["status"],
    }


def _lancamento(linha: dict[str, str], cliente_id: str) -> dict[str, Any]:
    return {
        "id": linha["id"],
        "cliente_id": cliente_id,
        "transacao_id": linha["transaction_id"],
        "transacao_original_id": linha["original_transaction_id"] or None,
        "lancado_em": datetime.fromisoformat(linha["booked_at"]),
        "valor_centavos": int(linha["amount_cents"]),
        "nome_contraparte": linha["counterparty_name"],
        "documento_contraparte": linha["counterparty_document"],
        "descricao": linha["description"],
        "status": linha["status"],
        "tipo": linha["kind"],
    }
