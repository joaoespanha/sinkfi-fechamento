"""Rotas com cliente no endereço. Todas passam por `checar_cliente`, no próprio router (ADR 0005)."""

from dataclasses import asdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from fechamento import Resumo
from sinkfi import lojista
from sinkfi.api.autenticacao import checar_cliente, exige_papel
from sinkfi.api.esquemas import (
    AtualizacaoLida,
    FechamentoResposta,
    ItemLido,
    LimiteEntrada,
    LimiteLido,
    ResumoLido,
    RodadaLida,
    SemanaEntrada,
    SemanaLida,
    ConferenciaEntrada,
    ConferenciaLida,
)
from sinkfi.api.relogio import obter_agora
from sinkfi.api.sessao import obter_sessao
from sinkfi.atualizacao import atualizacao
from sinkfi.banco import repositorios
from sinkfi.fila import Fila, obter_fila
from sinkfi.fechamentos import ancora_dos_cortes, corte_atual, corte_da_semana, fechamentos_do_cliente
from sinkfi.leitura import FechamentoLido, fechamento_da_rodada, fechamento_da_semana
from sinkfi.tipos import Papel, Conferencia, Usuario

rotas = APIRouter(prefix="/clientes/{cliente_id}", dependencies=[Depends(checar_cliente)])


@rotas.get("/semanas")
def listar_semanas(
    cliente_id: str, sessao: Session = Depends(obter_sessao), agora: datetime = Depends(obter_agora)
) -> list[SemanaLida]:
    """Os fechamentos que já passaram, do mais novo para o mais antigo (ADR 0007)."""
    semanas = fechamentos_do_cliente(sessao, cliente_id, agora, ancora_dos_cortes())
    return [SemanaLida(**asdict(s)) for s in semanas]


@rotas.get("/fechamento")
def ler_fechamento(
    cliente_id: str,
    semana: date | None = None,
    sessao: Session = Depends(obter_sessao),
    agora: datetime = Depends(obter_agora),
) -> FechamentoResposta:
    """A rodada mais recente da semana. Sem `semana`, a do fechamento atual."""
    if semana is None:
        atual = corte_atual(sessao, cliente_id, agora, ancora_dos_cortes())
        semana = atual.date() if atual else None
    lido = fechamento_da_semana(sessao, cliente_id, semana) if semana else None
    if lido is None:
        raise HTTPException(status_code=404, detail="semana sem rodada")
    return _fechamento_resposta(lido, agora)


@rotas.get("/rodadas")
def listar_rodadas(
    cliente_id: str, nsu: str | None = None, sessao: Session = Depends(obter_sessao)
) -> list[RodadaLida]:
    """Todas as rodadas, da mais nova para a mais antiga. Com `nsu`, só as que têm essa venda (Debugar)."""
    rodadas = (
        repositorios.rodadas_com_nsu(sessao, cliente_id, nsu)
        if nsu
        else repositorios.rodadas_do_cliente(sessao, cliente_id)
    )
    return [RodadaLida.model_validate(r) for r in rodadas]


@rotas.get("/rodadas/{rodada_id}")
def ler_rodada(
    cliente_id: str,
    rodada_id: int,
    sessao: Session = Depends(obter_sessao),
    agora: datetime = Depends(obter_agora),
) -> FechamentoResposta:
    """Uma rodada qualquer, inclusive a que já não é a mais recente: a que ela viu na conferência (Debugar)."""
    rodada = repositorios.rodada_do_cliente(sessao, cliente_id, rodada_id)
    if rodada is None:
        raise HTTPException(status_code=404, detail="rodada não encontrada")
    return _fechamento_resposta(fechamento_da_rodada(sessao, rodada), agora)


def _fechamento_resposta(lido: FechamentoLido, agora: datetime) -> FechamentoResposta:
    return FechamentoResposta(
        rodada=RodadaLida.model_validate(lido.rodada),
        resumo=_resumo_lido(lido.resumo, lido.limite_trava_centavos),
        itens=[ItemLido.model_validate({**asdict(i.item), "dia": i.dia}) for i in lido.itens],
        ultima_conferencia=_conferencia_lida(lido.ultima_conferencia) if lido.ultima_conferencia else None,
        # Do cliente agora, não da rodada: a rodada antiga (Debugar) também diz até quando há dado.
        atualizacao=AtualizacaoLida.model_validate(atualizacao(lido.ultima_ingestao_em, agora)),
    )


@rotas.get("/limite")
def ler_limite(cliente_id: str, sessao: Session = Depends(obter_sessao)) -> LimiteLido:
    """O limite atual, com ou sem fechamento: é o que a tela de Limite mostra (#25). Lojista e suporte."""
    return LimiteLido(limite_trava_centavos=repositorios.limite_do_cliente(sessao, cliente_id))


@rotas.put("/limite", status_code=status.HTTP_204_NO_CONTENT)
def mudar_limite(
    cliente_id: str,
    entrada: LimiteEntrada,
    usuario: Usuario = Depends(exige_papel(Papel.LOJISTA)),
    sessao: Session = Depends(obter_sessao),
) -> None:
    lojista.mudar_limite(sessao, cliente_id, usuario, entrada.limite_trava_centavos)
    sessao.commit()


@rotas.post("/conferencias", status_code=status.HTTP_201_CREATED)
def registrar_conferencia(
    cliente_id: str,
    entrada: ConferenciaEntrada,
    usuario: Usuario = Depends(exige_papel(Papel.LOJISTA)),
    sessao: Session = Depends(obter_sessao),
) -> ConferenciaLida:
    conferencia = lojista.conferir(sessao, cliente_id, usuario, entrada.rodada_id)
    if conferencia is None:
        raise HTTPException(status_code=404, detail="rodada não encontrada")
    sessao.commit()
    return _conferencia_lida(conferencia)


@rotas.post("/fechamentos", status_code=status.HTTP_202_ACCEPTED, response_class=Response)
def pedir_fechamento(
    cliente_id: str,
    entrada: SemanaEntrada,
    sessao: Session = Depends(obter_sessao),
    fila: Fila = Depends(obter_fila),
    agora: datetime = Depends(obter_agora),
) -> Response:
    """Pede o cálculo de uma semana da lista, pela fila (ADR 0004 e 0007). Lojista e suporte."""
    corte = _corte_da_lista(sessao, cliente_id, agora, entrada.semana)
    fila.pedir_fechamento_da_semana(cliente_id, corte)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@rotas.post(
    "/reprocessar",
    status_code=status.HTTP_202_ACCEPTED,
    response_class=Response,
    dependencies=[Depends(exige_papel(Papel.SUPORTE))],
)
def pedir_reprocessamento(
    cliente_id: str,
    entrada: SemanaEntrada,
    sessao: Session = Depends(obter_sessao),
    fila: Fila = Depends(obter_fila),
    agora: datetime = Depends(obter_agora),
) -> Response:
    """Enfileira o pedido e responde na hora: a rodada nova aparece quando o worker terminar (ADR 0004)."""
    corte = _corte_da_lista(sessao, cliente_id, agora, entrada.semana)
    if fechamento_da_semana(sessao, cliente_id, entrada.semana) is None:
        raise HTTPException(status_code=404, detail="semana sem rodada")
    fila.pedir_reprocessamento(cliente_id, corte)
    return Response(status_code=status.HTTP_202_ACCEPTED)


def _corte_da_lista(sessao: Session, cliente_id: str, agora: datetime, semana: date) -> datetime:
    corte = corte_da_semana(sessao, cliente_id, agora, ancora_dos_cortes(), semana)
    if corte is None:
        raise HTTPException(status_code=422, detail="semana fora da lista")
    return corte


def _resumo_lido(resumo: Resumo, limite_trava_centavos: int | None) -> ResumoLido:
    return ResumoLido(
        recomendacao=resumo.recomendacao,
        falta_de_verdade_centavos=resumo.falta_de_verdade_centavos,
        itens_falta_de_verdade=resumo.itens_falta_de_verdade,
        itens_para_conferir=resumo.itens_para_conferir,
        limite_trava_centavos=limite_trava_centavos,
    )


def _conferencia_lida(conferencia: Conferencia) -> ConferenciaLida:
    return ConferenciaLida(
        quem=conferencia.quem,
        em=conferencia.em,
        rodada_id=conferencia.rodada_id,
        limite_trava_centavos=conferencia.limite_trava_centavos,
        resumo=_resumo_lido(conferencia.resumo, conferencia.limite_trava_centavos),
    )
