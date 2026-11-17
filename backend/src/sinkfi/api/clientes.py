"""Rotas com cliente no endereço. Todas passam por `checar_cliente`, no próprio router (ADR 0005)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fechamento import Resumo
from sinkfi import lojista
from sinkfi.api.autenticacao import checar_cliente, exige_papel
from sinkfi.api.esquemas import (
    FechamentoResposta,
    ItemLido,
    LimiteEntrada,
    ResumoLido,
    RodadaLida,
    TermineiEntrada,
    TerminoLido,
)
from sinkfi.api.sessao import obter_sessao
from sinkfi.leitura import fechamento_mais_recente
from sinkfi.rodadas import reprocessar
from sinkfi.tipos import Papel, Termino, Usuario

rotas = APIRouter(prefix="/clientes/{cliente_id}", dependencies=[Depends(checar_cliente)])


@rotas.get("/fechamento")
def ler_fechamento(cliente_id: str, sessao: Session = Depends(obter_sessao)) -> FechamentoResposta:
    lido = fechamento_mais_recente(sessao, cliente_id)
    if lido is None:
        raise HTTPException(status_code=404, detail="cliente sem rodada")
    return FechamentoResposta(
        rodada=RodadaLida.model_validate(lido.rodada),
        resumo=_resumo_lido(lido.resumo, lido.limite_trava_centavos),
        itens=[ItemLido.model_validate(i) for i in lido.itens],
        ultimo_termino=_termino_lido(lido.ultimo_termino) if lido.ultimo_termino else None,
    )


@rotas.put("/limite", status_code=status.HTTP_204_NO_CONTENT)
def mudar_limite(
    cliente_id: str,
    entrada: LimiteEntrada,
    usuario: Usuario = Depends(exige_papel(Papel.LOJISTA)),
    sessao: Session = Depends(obter_sessao),
) -> None:
    lojista.mudar_limite(sessao, cliente_id, usuario, entrada.limite_trava_centavos)
    sessao.commit()


@rotas.post("/terminei", status_code=status.HTTP_201_CREATED)
def marcar_terminei(
    cliente_id: str,
    entrada: TermineiEntrada,
    usuario: Usuario = Depends(exige_papel(Papel.LOJISTA)),
    sessao: Session = Depends(obter_sessao),
) -> TerminoLido:
    termino = lojista.terminar(sessao, cliente_id, usuario, entrada.rodada_id)
    if termino is None:
        raise HTTPException(status_code=404, detail="rodada não encontrada")
    sessao.commit()
    return _termino_lido(termino)


@rotas.post("/reprocessar", dependencies=[Depends(exige_papel(Papel.SUPORTE))])
def pedir_reprocessamento(cliente_id: str, sessao: Session = Depends(obter_sessao)) -> RodadaLida:
    # Síncrono até o #10, que troca por enfileirar (plano de corte do ADR 0004).
    rodada = reprocessar(sessao, cliente_id)
    if rodada is None:
        raise HTTPException(status_code=404, detail="cliente sem rodada")
    sessao.commit()
    return RodadaLida.model_validate(rodada)


def _resumo_lido(resumo: Resumo, limite_trava_centavos: int | None) -> ResumoLido:
    return ResumoLido(
        recomendacao=resumo.recomendacao,
        falta_de_verdade_centavos=resumo.falta_de_verdade_centavos,
        itens_falta_de_verdade=resumo.itens_falta_de_verdade,
        itens_para_conferir=resumo.itens_para_conferir,
        limite_trava_centavos=limite_trava_centavos,
    )


def _termino_lido(termino: Termino) -> TerminoLido:
    return TerminoLido(
        quem=termino.quem,
        em=termino.em,
        rodada_id=termino.rodada_id,
        limite_trava_centavos=termino.limite_trava_centavos,
        resumo=_resumo_lido(termino.resumo, termino.limite_trava_centavos),
    )
