from datetime import datetime

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

# A adquirente é reconhecida pelo documento da contraparte, nunca pelo nome.
DOCUMENTO_DA_ADQUIRENTE = {
    "stone": "16501555000100",
    "pagseguro": "08561701000100",
}

CANCELADO = "cancelled"
CHARGEBACK = "chargeback"


def fechar(
    recebiveis: list[Recebivel],
    lancamentos: list[Lancamento],
    lojas: list[Loja],
    corte: datetime,
) -> Fechamento:
    lancamentos = _normalizar(lancamentos)
    creditos = [l for l in lancamentos if l.tipo != CHARGEBACK]
    desfeitos = {l.transacao_original_id for l in lancamentos if l.tipo == CHARGEBACK}

    vencidos = [r for r in recebiveis if r.liquidacao_prevista <= corte.date()]
    ativos = [r for r in vencidos if r.status != CANCELADO]
    cancelados = [r for r in vencidos if r.status == CANCELADO]

    grupos: list[GrupoDeRecebiveis] = []
    pendencias: list[Pendencia] = []
    casados: set[str] = set()

    for recebivel in ativos:
        do_recebivel = [c for c in creditos if _chave_forte(recebivel, c)]
        casados.update(c.id for c in do_recebivel)
        valem = [c for c in do_recebivel if c.transacao_id not in desfeitos]
        estornado = sum(c.valor_centavos for c in do_recebivel if c.transacao_id in desfeitos)
        caiu = sum(c.valor_centavos for c in valem if c.lancado_em <= corte)
        proximo = sum(c.valor_centavos for c in valem if c.lancado_em > corte)
        nao_caiu = max(recebivel.liquido_centavos - caiu - proximo, 0)

        grupo = GrupoDeRecebiveis(
            recebiveis=[recebivel],
            creditos=do_recebivel,
            esperado_centavos=recebivel.liquido_centavos,
            caiu_centavos=caiu,
            nao_caiu_centavos=nao_caiu,
            proximo_fechamento_centavos=proximo,
        )
        grupos.append(grupo)
        if nao_caiu:
            pendencias.append(_falta(grupo, estornado))

    for recebivel in cancelados:
        for credito in creditos:
            if _chave_forte(recebivel, credito):
                casados.add(credito.id)
                pendencias.append(
                    Pendencia(
                        Severidade.FALTA_DE_VERDADE,
                        Motivo.VENDA_CANCELADA,
                        credito.valor_centavos,
                        lancamento=credito,
                    )
                )

    for credito in creditos:
        if credito.id not in casados:
            pendencias.append(
                Pendencia(
                    Severidade.PARA_CONFERIR,
                    Motivo.ENTRADA_SEM_RECEBIVEL,
                    credito.valor_centavos,
                    lancamento=credito,
                )
            )

    return Fechamento(grupos=grupos, pendencias=pendencias)


def _falta(grupo: GrupoDeRecebiveis, estornado: int) -> Pendencia:
    """O que não caiu vira uma pendência só, com o motivo que explica a falta."""
    if estornado:
        motivo = Motivo.CHARGEBACK
    elif grupo.caiu_centavos or grupo.proximo_fechamento_centavos:
        motivo = Motivo.CAIU_EM_PARTE
    else:
        motivo = Motivo.NAO_CAIU
    return Pendencia(Severidade.FALTA_DE_VERDADE, motivo, grupo.nao_caiu_centavos, grupo=grupo)


def _chave_forte(recebivel: Recebivel, lancamento: Lancamento) -> bool:
    """NSU citado na descrição de um crédito que vem da adquirente do recebível."""
    return (
        recebivel.nsu in lancamento.descricao
        and lancamento.documento_contraparte == DOCUMENTO_DA_ADQUIRENTE[recebivel.adquirente]
    )


def _normalizar(lancamentos: list[Lancamento]) -> list[Lancamento]:
    """Lançamentos repetidos com a mesma transação são um só."""
    por_transacao: dict[str, Lancamento] = {}
    for lancamento in lancamentos:
        por_transacao.setdefault(lancamento.transacao_id, lancamento)
    return list(por_transacao.values())
