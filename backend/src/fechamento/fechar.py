"""Fechamento em etapas (ADR 0001): normalizar, casar, agrupar, cortar e classificar."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, tzinfo

from fechamento.tipos import (
    Fechamento,
    GrupoDeRecebiveis,
    Lancamento,
    Loja,
    Motivo,
    Pendencia,
    Recebivel,
    Severidade,
)

# Sobe a cada mudança de comportamento da regra. Entra no hash da rodada (ADR 0006).
VERSAO_DA_REGRA = "2"

# A adquirente é reconhecida pelo documento da contraparte, nunca pelo nome.
DOCUMENTO_DA_ADQUIRENTE = {
    "stone": "16501555000100",
    "pagseguro": "08561701000100",
}

# Janela da chave fraca, em dias corridos em torno da liquidação prevista.
DIAS_ANTES_CHAVE_FRACA = 1
DIAS_DEPOIS_CHAVE_FRACA = 4

CANCELADO = "cancelled"
CHARGEBACK = "chargeback"
PIX = "pix"
PIX_RECEBIDO = "pix_in"
PENDENTE = "pending"
# Tarifa da conta e transferência da própria titular não são crédito.
NAO_E_CREDITO = {"fee", "internal_transfer"}

PARCELA_NA_DESCRICAO = re.compile(r"(\d+)/(\d+)")


def fechar(
    recebiveis: list[Recebivel],
    lancamentos: list[Lancamento],
    lojas: list[Loja],
    corte: datetime,
) -> Fechamento:
    lancamentos = _normalizar(lancamentos)
    creditos = [l for l in lancamentos if l.tipo != CHARGEBACK]
    desfeitos = {l.transacao_original_id for l in lancamentos if l.tipo == CHARGEBACK}

    casamento = _casar(recebiveis, creditos, corte.tzinfo)

    esperados = [
        r for r in recebiveis if r.status != CANCELADO and r.liquidacao_prevista <= corte.date()
    ]
    grupos = [
        _grupo(recs, creditos_do_grupo, desfeitos, corte)
        for recs, creditos_do_grupo in _agrupar(esperados, creditos, casamento)
    ]

    pendencias = [_falta(g, desfeitos) for g in grupos if g.nao_caiu_centavos]
    ids_esperados = {r.id for r in esperados}
    for credito in creditos:
        motivo = _motivo_da_entrada(credito, casamento, ids_esperados)
        if motivo:
            pendencias.append(_entrada(credito, motivo))

    return Fechamento(grupos=grupos, pendencias=pendencias)


# Normalizar


def _normalizar(lancamentos: list[Lancamento]) -> list[Lancamento]:
    """Lançamentos repetidos com a mesma transação são um só, e o que não é crédito sai.

    Entre as repetições, a confirmada vale mais que a `pending`: é o mesmo dinheiro, já na conta.
    """
    por_transacao: dict[str, Lancamento] = {}
    for lancamento in lancamentos:
        if lancamento.tipo in NAO_E_CREDITO:
            continue
        atual = por_transacao.get(lancamento.transacao_id)
        if atual is None or (atual.status == PENDENTE and lancamento.status != PENDENTE):
            por_transacao[lancamento.transacao_id] = lancamento
    return list(por_transacao.values())


# Casar


@dataclass
class _Casamento:
    """Recebíveis que cada crédito paga. Um crédito com vários recebíveis forma grupo."""

    recebiveis_do_credito: dict[str, list[Recebivel]] = field(default_factory=dict)
    ligados_a_venda: set[str] = field(default_factory=set)
    pagos: set[str] = field(default_factory=set)

    def casa(self, credito: Lancamento, recebiveis: list[Recebivel]) -> None:
        self.recebiveis_do_credito[credito.id] = recebiveis
        self.pagos.update(r.id for r in recebiveis)


def _casar(recebiveis: list[Recebivel], creditos: list[Lancamento], fuso: tzinfo | None) -> _Casamento:
    casamento = _Casamento()
    sem_parcela: list[tuple[Lancamento, list[Recebivel]]] = []
    sem_nsu: list[Lancamento] = []

    # 1. Chave forte: um recebível com o NSU, ou a parcela que a descrição indica.
    for credito in creditos:
        candidatos = [r for r in recebiveis if _chave_forte(r, credito)]
        parcela = PARCELA_NA_DESCRICAO.search(credito.descricao)
        if len(candidatos) == 1:
            casamento.casa(credito, candidatos)
        elif candidatos and parcela:
            indicada = [r for r in candidatos if r.parcela == int(parcela.group(1))]
            if indicada:
                casamento.casa(credito, indicada)
        elif candidatos:
            sem_parcela.append((credito, candidatos))
        elif not any(r.nsu in credito.descricao for r in recebiveis):
            sem_nsu.append(credito)

    # 2. NSU de venda parcelada sem "n/m": parcelas vencidas até o crédito, sem crédito, mesmo líquido.
    for credito, parcelas in sem_parcela:
        dia = _dia(credito, fuso)
        abertas = [
            r
            for r in parcelas
            if r.liquidacao_prevista <= dia
            and r.id not in casamento.pagos
            and r.liquido_centavos == credito.valor_centavos
        ]
        if abertas:
            casamento.casa(credito, abertas)
        else:
            casamento.ligados_a_venda.add(credito.id)

    # 3. Chave fraca: crédito sem NSU, mesma adquirente, valor exato, dentro da janela.
    for credito in sem_nsu:
        dia = _dia(credito, fuso)
        candidatos = [
            r
            for r in recebiveis
            if r.status != CANCELADO and r.id not in casamento.pagos and _chave_fraca(r, credito, dia)
        ]
        if candidatos:
            casamento.casa(credito, candidatos)

    return casamento


def _chave_forte(recebivel: Recebivel, lancamento: Lancamento) -> bool:
    """NSU citado na descrição de um crédito da adquirente do recebível, ou Pix para recebível Pix."""
    if recebivel.nsu not in lancamento.descricao:
        return False
    if recebivel.trilho == PIX:
        return lancamento.tipo == PIX_RECEBIDO
    return lancamento.documento_contraparte == DOCUMENTO_DA_ADQUIRENTE.get(recebivel.adquirente)


def _chave_fraca(recebivel: Recebivel, credito: Lancamento, dia: date) -> bool:
    inicio = max(recebivel.vendido_em, recebivel.liquidacao_prevista - timedelta(days=DIAS_ANTES_CHAVE_FRACA))
    fim = recebivel.liquidacao_prevista + timedelta(days=DIAS_DEPOIS_CHAVE_FRACA)
    return (
        credito.documento_contraparte == DOCUMENTO_DA_ADQUIRENTE.get(recebivel.adquirente)
        and credito.valor_centavos == recebivel.liquido_centavos
        and inicio <= dia <= fim
    )


def _dia(lancamento: Lancamento, fuso: tzinfo | None) -> date:
    """Data do lançamento no fuso do corte do cliente."""
    return lancamento.lancado_em.astimezone(fuso).date()


# Agrupar e cortar


def _agrupar(
    esperados: list[Recebivel], creditos: list[Lancamento], casamento: _Casamento
) -> list[tuple[list[Recebivel], list[Lancamento]]]:
    """Recebíveis ligados por um mesmo crédito ficam num grupo só (ADR 0002)."""
    dono = {r.id: r.id for r in esperados}

    def raiz(id: str) -> str:
        while dono[id] != id:
            id = dono[id]
        return id

    for recebiveis in casamento.recebiveis_do_credito.values():
        ids = [r.id for r in recebiveis if r.id in dono]
        for outro in ids[1:]:
            dono[raiz(outro)] = raiz(ids[0])

    por_raiz: dict[str, list[Recebivel]] = {}
    for recebivel in esperados:
        por_raiz.setdefault(raiz(recebivel.id), []).append(recebivel)

    grupos = []
    for recebiveis in por_raiz.values():
        ids = {r.id for r in recebiveis}
        do_grupo = [
            c
            for c in creditos
            if any(r.id in ids for r in casamento.recebiveis_do_credito.get(c.id, []))
        ]
        grupos.append((recebiveis, do_grupo))
    return grupos


def _caiu_ate(credito: Lancamento, corte: datetime) -> bool:
    """Confirmado e lançado até o corte. O `pending` casado entra no próximo fechamento."""
    return credito.status != PENDENTE and credito.lancado_em <= corte


def _grupo(
    recebiveis: list[Recebivel], creditos: list[Lancamento], desfeitos: set[str | None], corte: datetime
) -> GrupoDeRecebiveis:
    valem = [c for c in creditos if c.transacao_id not in desfeitos]
    esperado = sum(r.liquido_centavos for r in recebiveis)
    caiu = sum(c.valor_centavos for c in valem if _caiu_ate(c, corte))
    proximo = sum(c.valor_centavos for c in valem if not _caiu_ate(c, corte))
    return GrupoDeRecebiveis(
        recebiveis=recebiveis,
        creditos=creditos,
        esperado_centavos=esperado,
        caiu_centavos=caiu,
        nao_caiu_centavos=max(esperado - caiu - proximo, 0),
        proximo_fechamento_centavos=proximo,
    )


# Classificar


def _falta(grupo: GrupoDeRecebiveis, desfeitos: set[str | None]) -> Pendencia:
    """O que não caiu vira uma pendência só, com o motivo que explica a falta."""
    if any(c.transacao_id in desfeitos for c in grupo.creditos):
        motivo = Motivo.CHARGEBACK
    elif len(grupo.recebiveis) > 1:
        motivo = Motivo.GRUPO_NAO_FECHA
    elif grupo.caiu_centavos or grupo.proximo_fechamento_centavos:
        motivo = Motivo.CAIU_EM_PARTE
    else:
        motivo = Motivo.NAO_CAIU
    return Pendencia(Severidade.FALTA_DE_VERDADE, motivo, grupo.nao_caiu_centavos, grupo=grupo)


def _motivo_da_entrada(credito: Lancamento, casamento: _Casamento, ids_esperados: set[str]) -> Motivo | None:
    """Crédito que não paga nenhum recebível esperado deste fechamento."""
    if credito.id in casamento.ligados_a_venda:
        return Motivo.PODE_SER_ANTECIPACAO
    recebiveis = casamento.recebiveis_do_credito.get(credito.id)
    if not recebiveis:
        return Motivo.ENTRADA_SEM_RECEBIVEL
    if any(r.id in ids_esperados for r in recebiveis):
        return None
    if all(r.status == CANCELADO for r in recebiveis):
        return Motivo.VENDA_CANCELADA
    return Motivo.PODE_SER_ANTECIPACAO


_SEVERIDADE_DA_ENTRADA = {
    Motivo.VENDA_CANCELADA: Severidade.FALTA_DE_VERDADE,
    Motivo.ENTRADA_SEM_RECEBIVEL: Severidade.PARA_CONFERIR,
    Motivo.PODE_SER_ANTECIPACAO: Severidade.PARA_CONFERIR,
}


def _entrada(credito: Lancamento, motivo: Motivo) -> Pendencia:
    return Pendencia(_SEVERIDADE_DA_ENTRADA[motivo], motivo, credito.valor_centavos, lancamento=credito)
