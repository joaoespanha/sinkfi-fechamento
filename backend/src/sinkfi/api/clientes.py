"""Rotas com cliente no endereço. Todas passam por `checar_cliente`, no próprio router (ADR 0005)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from sinkfi.api.autenticacao import checar_cliente, exige_papel
from sinkfi.api.esquemas import FechamentoResposta, ItemLido, LimiteEntrada, ResumoLido, RodadaLida
from sinkfi.api.sessao import obter_sessao
from sinkfi.banco import repositorios
from sinkfi.leitura import fechamento_mais_recente
from sinkfi.rodadas import reprocessar
from sinkfi.tipos import Papel

rotas = APIRouter(prefix="/clientes/{cliente_id}", dependencies=[Depends(checar_cliente)])


@rotas.get("/fechamento")
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


@rotas.put(
    "/limite",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(exige_papel(Papel.LOJISTA))],
)
def mudar_limite(cliente_id: str, entrada: LimiteEntrada, sessao: Session = Depends(obter_sessao)) -> None:
    repositorios.definir_limite(sessao, cliente_id, entrada.limite_trava_centavos)
    sessao.commit()


@rotas.post("/reprocessar", dependencies=[Depends(exige_papel(Papel.SUPORTE))])
def pedir_reprocessamento(cliente_id: str, sessao: Session = Depends(obter_sessao)) -> RodadaLida:
    # Síncrono até o #10, que troca por enfileirar (plano de corte do ADR 0004).
    rodada = reprocessar(sessao, cliente_id)
    if rodada is None:
        raise HTTPException(status_code=404, detail="cliente sem rodada")
    sessao.commit()
    return RodadaLida.model_validate(rodada)
