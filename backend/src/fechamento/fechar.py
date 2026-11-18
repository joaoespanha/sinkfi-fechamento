"""Fechamento em etapas (ADR 0001): normalizar, casar, agrupar, cortar e classificar."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, tzinfo

from fechamento.tipos import (
    Fechamento,
    GrupoDeRecebiveis,
    Identidade,
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

# "n/m" solto: não pega pedaço de data como "10/11/2026" nem de um número maior.
PARCELA_NA_DESCRICAO = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])")


def fechar(
    recebiveis: list[Recebivel],
    lancamentos: list[Lancamento],
    lojas: list[Loja],
    corte: datetime,
) -> Fechamento:
    lancamentos = _normalizar(lancamentos)
    creditos = [l for l in lancamentos if l.tipo != CHARGEBACK]
    # Quanto cada transação perdeu por chargeback. O chargeback desfaz só o seu valor.
    desfeitos: dict[str, int] = {}
    for l in lancamentos:
        if l.tipo == CHARGEBACK and l.transacao_original_id:
            desfeitos[l.transacao_original_id] = desfeitos.get(l.transacao_original_id, 0) + l.valor_centavos

    casamento = _casar(recebiveis, creditos, corte.tzinfo)

    esperados = [
        r for r in recebiveis if r.status != CANCELADO and r.liquidacao_prevista <= corte.date()
    ]
    grupos = [
        _grupo(recs, creditos_do_grupo, desfeitos, corte)
        for recs, creditos_do_grupo in _agrupar(esperados, creditos, casamento)
    ]

    pendencias = [_falta(g, desfeitos) for g in grupos if g.nao_caiu_centavos]
    pendencias += [_a_mais(g, sobra) for g in grupos if (sobra := _sobra(g, desfeitos))]
    identidades_esperadas = {r.identidade for r in esperados}
    for credito in creditos:
        fica = _valor_que_fica(credito, desfeitos)
        if fica == 0:
            continue  # Entrou e saiu inteiro por chargeback: não há o que conferir.
        motivo = _motivo_da_entrada(credito, casamento, identidades_esperadas)
        if motivo:
            pendencias.append(_entrada(credito, motivo, fica))

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
    pagos: set[Identidade] = field(default_factory=set)

    def casa(self, credito: Lancamento, recebiveis: list[Recebivel]) -> None:
        self.recebiveis_do_credito[credito.id] = recebiveis
        self.pagos.update(r.identidade for r in recebiveis)


def _casar(recebiveis: list[Recebivel], creditos: list[Lancamento], fuso: tzinfo | None) -> _Casamento:
    casamento = _Casamento()
    sem_parcela: list[tuple[Lancamento, list[Recebivel]]] = []
    sem_nsu: list[Lancamento] = []

    # 1. Chave forte: um recebível com o NSU, ou a parcela que a descrição indica.
    for credito in creditos:
        candidatos = [r for r in recebiveis if _chave_forte(r, credito)]
        parcela = _parcela_indicada(credito.descricao, candidatos)
        if len(candidatos) == 1:
            casamento.casa(credito, candidatos)
        elif candidatos and parcela:
            indicada = [r for r in candidatos if r.parcela == parcela]
            if indicada:
                casamento.casa(credito, indicada)
            else:
                # A parcela indicada não existe: o crédito é da venda, mas não paga nenhum recebível dela.
                casamento.ligados_a_venda.add(credito.id)
        elif candidatos:
            sem_parcela.append((credito, candidatos))
        elif not any(_cita_nsu(r.nsu, credito.descricao) for r in recebiveis):
            sem_nsu.append(credito)

    # 2. NSU de venda parcelada sem "n/m": parcelas vencidas até o crédito, sem crédito, mesmo líquido.
    for credito, parcelas in sem_parcela:
        dia = _dia(credito, fuso)
        abertas = [
            r
            for r in parcelas
            if r.liquidacao_prevista <= dia
            and r.identidade not in casamento.pagos
            and r.liquido_centavos == credito.valor_centavos
        ]
        if abertas:
            casamento.casa(credito, abertas)
        else:
            casamento.ligados_a_venda.add(credito.id)

    # 3. Chave fraca: crédito sem NSU, mesma adquirente, valor exato, dentro da janela.
    # Créditos com os mesmos candidatos são um empate só: até um crédito por candidato casa
    # com todos eles, num grupo (ADR 0002). O crédito que passa disso fica sem recebível.
    pagos_pela_chave_forte = set(casamento.pagos)
    empates: dict[frozenset[Identidade], tuple[list[Recebivel], list[Lancamento]]] = {}
    for credito in sem_nsu:
        dia = _dia(credito, fuso)
        candidatos = [
            r
            for r in recebiveis
            if r.status != CANCELADO and r.identidade not in pagos_pela_chave_forte and _chave_fraca(r, credito, dia)
        ]
        if candidatos:
            empates.setdefault(frozenset(r.identidade for r in candidatos), (candidatos, []))[1].append(credito)
    for candidatos, creditos_do_empate in empates.values():
        livres = [r for r in candidatos if r.identidade not in casamento.pagos]
        for credito in sorted(creditos_do_empate, key=lambda c: c.lancado_em)[: len(livres)]:
            casamento.casa(credito, livres)

    return casamento


def _cita_nsu(nsu: str, descricao: str) -> bool:
    """O NSU aparece inteiro na descrição: "STN-1" não está em "STN-12"."""
    return re.search(rf"(?<![0-9A-Za-z]){re.escape(nsu)}(?![0-9A-Za-z])", descricao) is not None


def _parcela_indicada(descricao: str, candidatos: list[Recebivel]) -> int | None:
    """O "n/m" da descrição cujo m é o número de parcelas da venda."""
    parcelas = {r.parcelas for r in candidatos}
    for achado in PARCELA_NA_DESCRICAO.finditer(descricao):
        if int(achado.group(2)) in parcelas:
            return int(achado.group(1))
    return None


def _chave_forte(recebivel: Recebivel, lancamento: Lancamento) -> bool:
    """NSU citado na descrição de um crédito da adquirente do recebível, ou Pix para recebível Pix."""
    if not _cita_nsu(recebivel.nsu, lancamento.descricao):
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
    dono: dict[Identidade, Identidade] = {r.identidade: r.identidade for r in esperados}

    def raiz(identidade: Identidade) -> Identidade:
        while dono[identidade] != identidade:
            identidade = dono[identidade]
        return identidade

    for recebiveis in casamento.recebiveis_do_credito.values():
        ligados = [r.identidade for r in recebiveis if r.identidade in dono]
        for outro in ligados[1:]:
            dono[raiz(outro)] = raiz(ligados[0])

    por_raiz: dict[Identidade, list[Recebivel]] = {}
    for recebivel in esperados:
        por_raiz.setdefault(raiz(recebivel.identidade), []).append(recebivel)

    grupos = []
    for recebiveis in por_raiz.values():
        identidades_do_grupo = {r.identidade for r in recebiveis}
        do_grupo = [
            c
            for c in creditos
            if any(r.identidade in identidades_do_grupo for r in casamento.recebiveis_do_credito.get(c.id, []))
        ]
        grupos.append((recebiveis, do_grupo))
    return grupos


def _valor_que_fica(credito: Lancamento, desfeitos: dict[str, int]) -> int:
    """O crédito menos o que o chargeback desfez dele."""
    return max(credito.valor_centavos - desfeitos.get(credito.transacao_id, 0), 0)


def _caiu_ate(credito: Lancamento, corte: datetime) -> bool:
    """Confirmado e lançado até o corte. O `pending` casado entra no próximo fechamento."""
    return credito.status != PENDENTE and credito.lancado_em <= corte


def _grupo(
    recebiveis: list[Recebivel], creditos: list[Lancamento], desfeitos: dict[str, int], corte: datetime
) -> GrupoDeRecebiveis:
    esperado = sum(r.liquido_centavos for r in recebiveis)
    caiu = sum(_valor_que_fica(c, desfeitos) for c in creditos if _caiu_ate(c, corte))
    proximo = sum(_valor_que_fica(c, desfeitos) for c in creditos if not _caiu_ate(c, corte))
    # Esperado = Caiu + Não caiu + Próximo fechamento, sempre. O que passa do esperado é a sobra.
    caiu = min(caiu, esperado)
    proximo = min(proximo, esperado - caiu)
    return GrupoDeRecebiveis(
        recebiveis=recebiveis,
        creditos=creditos,
        esperado_centavos=esperado,
        caiu_centavos=caiu,
        nao_caiu_centavos=esperado - caiu - proximo,
        proximo_fechamento_centavos=proximo,
    )


def _sobra(grupo: GrupoDeRecebiveis, desfeitos: dict[str, int]) -> int:
    """O que entrou para o grupo além do esperado."""
    entrou = sum(_valor_que_fica(c, desfeitos) for c in grupo.creditos)
    return max(entrou - grupo.esperado_centavos, 0)


# Classificar


def _falta(grupo: GrupoDeRecebiveis, desfeitos: dict[str, int]) -> Pendencia:
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


def _a_mais(grupo: GrupoDeRecebiveis, sobra: int) -> Pendencia:
    """Entrou mais do que o grupo vale. A sobra não é da lojista (GLOSSARY: Falta de verdade)."""
    return Pendencia(Severidade.FALTA_DE_VERDADE, Motivo.CAIU_A_MAIS, sobra, grupo=grupo)


def _motivo_da_entrada(
    credito: Lancamento, casamento: _Casamento, identidades_esperadas: set[Identidade]
) -> Motivo | None:
    """Crédito que não paga nenhum recebível esperado deste fechamento."""
    if credito.id in casamento.ligados_a_venda:
        return Motivo.PODE_SER_ANTECIPACAO
    recebiveis = casamento.recebiveis_do_credito.get(credito.id)
    if not recebiveis:
        return Motivo.ENTRADA_SEM_RECEBIVEL
    if any(r.identidade in identidades_esperadas for r in recebiveis):
        return None
    if all(r.status == CANCELADO for r in recebiveis):
        return Motivo.VENDA_CANCELADA
    return Motivo.PODE_SER_ANTECIPACAO


_SEVERIDADE_DA_ENTRADA = {
    Motivo.VENDA_CANCELADA: Severidade.FALTA_DE_VERDADE,
    Motivo.ENTRADA_SEM_RECEBIVEL: Severidade.PARA_CONFERIR,
    Motivo.PODE_SER_ANTECIPACAO: Severidade.PARA_CONFERIR,
}


def _entrada(credito: Lancamento, motivo: Motivo, valor: int) -> Pendencia:
    return Pendencia(_SEVERIDADE_DA_ENTRADA[motivo], motivo, valor, lancamento=credito)
