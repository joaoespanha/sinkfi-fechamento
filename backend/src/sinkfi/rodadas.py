"""Serviço da rodada: lê a entrada, identifica pelo hash e grava (ADR 0004 e 0006).

Não faz commit: quem chama é dono da transação.
"""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from fechamento import VERSAO_DA_REGRA
from sinkfi.banco import repositorios
from sinkfi.tipos import Entrada, Rodada


def rodar_fechamento(
    sessao: Session, cliente_id: str, corte: datetime, versao: str = VERSAO_DA_REGRA
) -> Rodada:
    entrada = repositorios.entrada_do_cliente(sessao, cliente_id)
    hash_entrada = hash_da_rodada(entrada, corte, versao)
    data_fechamento = corte.date()

    existente = repositorios.rodada_por_hash(sessao, cliente_id, data_fechamento, hash_entrada)
    if existente:
        return existente

    return repositorios.gravar_rodada(
        sessao,
        cliente_id=cliente_id,
        data_fechamento=data_fechamento,
        corte=corte,
        versao_regra=versao,
        hash_entrada=hash_entrada,
    )


def hash_da_rodada(entrada: Entrada, corte: datetime, versao: str) -> str:
    conteudo = {
        "recebiveis": _ordenados(entrada.recebiveis),
        "lancamentos": _ordenados(entrada.lancamentos),
        "lojas": _ordenados(entrada.lojas),
        "corte": corte.isoformat(),
        "versao": versao,
    }
    texto = json.dumps(conteudo, sort_keys=True, default=_serializar)
    return hashlib.sha256(texto.encode()).hexdigest()


def _ordenados(itens: list) -> list[dict]:
    return sorted((asdict(i) for i in itens), key=lambda d: d["id"])


def _serializar(valor: object) -> str:
    # O banco devolve horários no fuso da conexão; em UTC o mesmo instante dá o mesmo texto.
    if isinstance(valor, datetime):
        return valor.astimezone(UTC).isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    raise TypeError(f"não sei serializar {type(valor).__name__}")
