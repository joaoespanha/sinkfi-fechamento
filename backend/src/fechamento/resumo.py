from fechamento.tipos import Pendencia, Recomendacao, Resumo, Severidade


def resumo(pendencias: list[Pendencia], limite_trava_centavos: int | None = None) -> Resumo:
    faltas = [p for p in pendencias if p.severidade == Severidade.FALTA_DE_VERDADE]
    falta_centavos = sum(p.valor_centavos for p in faltas)

    if not faltas:
        recomendacao = Recomendacao.PODE_FECHAR
    elif limite_trava_centavos is None:
        recomendacao = Recomendacao.FALTAM
    elif falta_centavos > limite_trava_centavos:
        recomendacao = Recomendacao.NAO_FECHE
    else:
        recomendacao = Recomendacao.PODE_FECHAR

    return Resumo(
        recomendacao=recomendacao,
        falta_de_verdade_centavos=falta_centavos,
        itens_falta_de_verdade=len(faltas),
        itens_para_conferir=len(pendencias) - len(faltas),
    )
