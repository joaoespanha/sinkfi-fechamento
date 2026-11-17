"""Leitura e gravação no Postgres. Recebe e devolve tipos do núcleo e de `sinkfi.tipos`."""

from datetime import date, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from fechamento import Lancamento, Loja, Recebivel
from sinkfi.banco.modelos import LinhaCliente, LinhaLancamento, LinhaLoja, LinhaRecebivel, LinhaRodada
from sinkfi.tipos import Entrada, Rodada


def criar_cliente(
    sessao: Session,
    *,
    id: str,
    nome: str,
    dia_fechamento: int,
    hora_corte: time,
    fuso: str,
    limite_trava_centavos: int | None = None,
) -> None:
    sessao.add(
        LinhaCliente(
            id=id,
            nome=nome,
            dia_fechamento=dia_fechamento,
            hora_corte=hora_corte,
            fuso=fuso,
            limite_trava_centavos=limite_trava_centavos,
        )
    )
    sessao.flush()


def gravar_lojas(sessao: Session, linhas: list[dict[str, Any]]) -> None:
    _upsert(sessao, LinhaLoja, linhas)


def gravar_recebiveis(sessao: Session, linhas: list[dict[str, Any]]) -> None:
    _upsert(sessao, LinhaRecebivel, linhas)


def gravar_lancamentos(sessao: Session, linhas: list[dict[str, Any]]) -> None:
    _upsert(sessao, LinhaLancamento, linhas)


def _upsert(sessao: Session, modelo: type, linhas: list[dict[str, Any]]) -> None:
    """O reenvio traz o lote inteiro: linha nova entra, linha conhecida é sobrescrita."""
    if not linhas:
        return
    comando = insert(modelo)
    colunas = {c: comando.excluded[c] for c in linhas[0] if c != "id"}
    sessao.execute(comando.on_conflict_do_update(index_elements=["id"], set_=colunas), linhas)


def entrada_do_cliente(sessao: Session, cliente_id: str) -> Entrada:
    lojas = sessao.scalars(select(LinhaLoja).where(LinhaLoja.cliente_id == cliente_id)).all()
    recebiveis = sessao.scalars(
        select(LinhaRecebivel).join(LinhaLoja).where(LinhaLoja.cliente_id == cliente_id)
    ).all()
    lancamentos = sessao.scalars(
        select(LinhaLancamento).where(LinhaLancamento.cliente_id == cliente_id)
    ).all()
    return Entrada(
        recebiveis=[_recebivel(r) for r in recebiveis],
        lancamentos=[_lancamento(l) for l in lancamentos],
        lojas=[Loja(id=l.id, documento=l.documento, adquirente=l.adquirente) for l in lojas],
    )


def rodada_por_hash(sessao: Session, cliente_id: str, data_fechamento: date, hash_entrada: str) -> Rodada | None:
    linha = sessao.scalars(
        select(LinhaRodada).where(
            LinhaRodada.cliente_id == cliente_id,
            LinhaRodada.data_fechamento == data_fechamento,
            LinhaRodada.hash_entrada == hash_entrada,
        )
    ).one_or_none()
    return _rodada(linha) if linha else None


def gravar_rodada(
    sessao: Session,
    *,
    cliente_id: str,
    data_fechamento: date,
    corte: datetime,
    versao_regra: str,
    hash_entrada: str,
) -> Rodada:
    linha = LinhaRodada(
        cliente_id=cliente_id,
        data_fechamento=data_fechamento,
        corte=corte,
        versao_regra=versao_regra,
        hash_entrada=hash_entrada,
    )
    sessao.add(linha)
    sessao.flush()
    return _rodada(linha)


def _recebivel(r: LinhaRecebivel) -> Recebivel:
    return Recebivel(
        id=r.id,
        loja_id=r.loja_id,
        adquirente=r.adquirente,
        trilho=r.trilho,
        vendido_em=r.vendido_em,
        liquidacao_prevista=r.liquidacao_prevista,
        liquido_centavos=r.liquido_centavos,
        nsu=r.nsu,
        parcela=r.parcela,
        parcelas=r.parcelas,
        status=r.status,
    )


def _lancamento(l: LinhaLancamento) -> Lancamento:
    return Lancamento(
        id=l.id,
        transacao_id=l.transacao_id,
        transacao_original_id=l.transacao_original_id,
        lancado_em=l.lancado_em,
        valor_centavos=l.valor_centavos,
        documento_contraparte=l.documento_contraparte,
        descricao=l.descricao,
        tipo=l.tipo,
    )


def _rodada(linha: LinhaRodada) -> Rodada:
    return Rodada(
        id=linha.id,
        cliente_id=linha.cliente_id,
        data_fechamento=linha.data_fechamento,
        corte=linha.corte,
        versao_regra=linha.versao_regra,
        hash_entrada=linha.hash_entrada,
    )


def rodadas_do_cliente(sessao: Session, cliente_id: str) -> list[Rodada]:
    """Da mais recente para a mais antiga. O `id` desempata rodadas da mesma transação,
    que recebem o mesmo `now()` em `criada_em`."""
    linhas = sessao.scalars(
        select(LinhaRodada)
        .where(LinhaRodada.cliente_id == cliente_id)
        .order_by(LinhaRodada.criada_em.desc(), LinhaRodada.id.desc())
    ).all()
    return [_rodada(l) for l in linhas]
