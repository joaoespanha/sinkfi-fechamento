"""Serviço da rodada: lê a entrada, identifica pelo hash e grava (ADR 0004 e 0006).

Não faz commit: quem chama é dono da transação.
"""

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from fechamento import VERSAO_DA_REGRA, Fechamento, fechar
from sinkfi.banco import repositorios
from sinkfi.tipos import ConfigFechamento, Entrada, ItemRodada, Rodada

log = logging.getLogger(__name__)


def rodar_fechamento(
    sessao: Session, cliente_id: str, corte: datetime, versao: str = VERSAO_DA_REGRA
) -> Rodada:
    # Dois pedidos do mesmo cliente ao mesmo tempo: o segundo espera o primeiro e acha a rodada pelo hash.
    # A ingestão trava o mesmo cliente, então a entrada lida aqui é a de antes ou a de depois dela, nunca metade.
    repositorios.travar_cliente(sessao, cliente_id)
    entrada = repositorios.entrada_do_cliente(sessao, cliente_id)
    hash_entrada = hash_da_rodada(entrada, corte, versao)
    data_fechamento = corte.date()

    existente = repositorios.rodada_por_hash(sessao, cliente_id, data_fechamento, hash_entrada)
    if existente:
        _registrar(existente, "existente", corte)
        return existente

    rodada = repositorios.gravar_rodada(
        sessao,
        cliente_id=cliente_id,
        data_fechamento=data_fechamento,
        corte=corte,
        versao_regra=versao,
        hash_entrada=hash_entrada,
    )
    fechamento = fechar(entrada.recebiveis, entrada.lancamentos, entrada.lojas, corte)
    repositorios.gravar_itens(sessao, rodada.id, itens_do_fechamento(fechamento))
    _registrar(rodada, "nova", corte)
    return rodada


def _registrar(rodada: Rodada, como: str, corte: datetime) -> None:
    # O corte como a regra recebeu, no fuso do cliente: é o mesmo texto que entra no hash.
    log.info(
        "rodada %s %s: cliente %s, corte %s, versão %s",
        rodada.id, como, rodada.cliente_id, corte.isoformat(), rodada.versao_regra,
    )


def reprocessar(sessao: Session, cliente_id: str, corte: datetime) -> Rodada:
    """Roda de novo o corte pedido, com a entrada de agora (ADR 0007).

    Sem entrada nova, o hash é o mesmo e a rodada existente volta.
    """
    return rodar_fechamento(sessao, cliente_id, corte)


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
    # A adquirente desempata recebíveis com o mesmo id (ADR 0009). Vem depois do id para que
    # a ordem, e o hash, das entradas sem id repetido não mudem.
    return sorted((asdict(i) for i in itens), key=lambda d: (d["id"], d.get("adquirente", "")))


def _serializar(valor: object) -> str:
    # O banco devolve horários no fuso da conexão; em UTC o mesmo instante dá o mesmo texto.
    if isinstance(valor, datetime):
        return valor.astimezone(UTC).isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    raise TypeError(f"não sei serializar {type(valor).__name__}")


def fechamento_vigente(config: ConfigFechamento, agora: datetime) -> datetime:
    """O último corte que já passou. Até o corte seguinte, as rodadas novas são dele."""
    fuso = ZoneInfo(config.fuso)
    local = agora.astimezone(fuso)
    dias_desde = (local.isoweekday() - config.dia_fechamento) % 7
    corte = datetime.combine(local.date() - timedelta(days=dias_desde), config.hora_corte, tzinfo=fuso)
    if corte > local:
        # Hoje é o dia do fechamento, mas antes da hora: vale o da semana passada.
        corte = datetime.combine(corte.date() - timedelta(days=7), config.hora_corte, tzinfo=fuso)
    return corte


def itens_do_fechamento(fechamento: Fechamento) -> list[ItemRodada]:
    """Um item por grupo e um por crédito que não paga recebível esperado."""
    itens = []
    for grupo in fechamento.grupos:
        falta = next((p for p in fechamento.pendencias if p.grupo is grupo), None)
        itens.append(
            ItemRodada(
                recebiveis=grupo.recebiveis,
                creditos=grupo.creditos,
                esperado_centavos=grupo.esperado_centavos,
                caiu_centavos=grupo.caiu_centavos,
                nao_caiu_centavos=grupo.nao_caiu_centavos,
                proximo_fechamento_centavos=grupo.proximo_fechamento_centavos,
                severidade=falta.severidade if falta else None,
                motivo=falta.motivo if falta else None,
                pendencia_centavos=falta.valor_centavos if falta else None,
            )
        )
    for pendencia in fechamento.pendencias:
        if pendencia.lancamento:
            itens.append(
                ItemRodada(
                    recebiveis=[],
                    creditos=[pendencia.lancamento],
                    severidade=pendencia.severidade,
                    motivo=pendencia.motivo,
                    pendencia_centavos=pendencia.valor_centavos,
                )
            )
    return itens
