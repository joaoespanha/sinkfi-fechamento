from datetime import datetime

from fechamento.tipos import Fechamento, GrupoDeRecebiveis, Lancamento, Loja, Recebivel

# A adquirente é reconhecida pelo documento da contraparte, nunca pelo nome.
DOCUMENTO_DA_ADQUIRENTE = {
    "stone": "16501555000100",
    "pagseguro": "08561701000100",
}


def fechar(
    recebiveis: list[Recebivel],
    lancamentos: list[Lancamento],
    lojas: list[Loja],
    corte: datetime,
) -> Fechamento:
    lancamentos = _normalizar(lancamentos)
    grupos = []
    for recebivel in recebiveis:
        creditos = [l for l in lancamentos if _chave_forte(recebivel, l)]
        ate_o_corte = sum(l.valor_centavos for l in creditos if l.lancado_em <= corte)
        depois_do_corte = sum(l.valor_centavos for l in creditos if l.lancado_em > corte)
        grupos.append(
            GrupoDeRecebiveis(
                recebiveis=[recebivel],
                creditos=creditos,
                esperado_centavos=recebivel.liquido_centavos,
                caiu_centavos=ate_o_corte,
                nao_caiu_centavos=0,
                proximo_fechamento_centavos=depois_do_corte,
            )
        )
    return Fechamento(grupos=grupos)


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
