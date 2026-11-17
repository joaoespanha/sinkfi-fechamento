from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sinkfi.api.esquemas import FechamentoResposta, ItemLido, ResumoLido, RodadaLida
from sinkfi.api.sessao import obter_sessao
from sinkfi.leitura import fechamento_mais_recente

rotas = APIRouter()


@rotas.get("/clientes/{cliente_id}/fechamento")
def ler_fechamento(cliente_id: str, sessao: Session = Depends(obter_sessao)) -> FechamentoResposta:
    lido = fechamento_mais_recente(sessao, cliente_id)
    if lido is None:
        raise HTTPException(status_code=404, detail="cliente sem rodada")
    return FechamentoResposta(
        rodada=RodadaLida.model_validate(lido.rodada),
        resumo=ResumoLido(
            recomendacao=lido.resumo.recomendacao,
            falta_de_verdade_centavos=lido.resumo.falta_de_verdade_centavos,
            itens_falta_de_verdade=lido.resumo.itens_falta_de_verdade,
            itens_para_conferir=lido.resumo.itens_para_conferir,
            limite_trava_centavos=lido.limite_trava_centavos,
        ),
        itens=[ItemLido.model_validate(i) for i in lido.itens],
    )
