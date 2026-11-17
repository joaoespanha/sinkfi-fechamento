"""Leitura e gravação no Postgres. Recebe e devolve tipos do núcleo e de `sinkfi.tipos`."""

from dataclasses import asdict
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from fechamento import Lancamento, Loja, Motivo, Recebivel, Severidade
from sinkfi.banco.modelos import (
    LinhaCliente,
    LinhaItemRodada,
    LinhaLancamento,
    LinhaLoja,
    LinhaRecebivel,
    LinhaRodada,
)
from sinkfi.tipos import Entrada, ItemRodada, Rodada


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


def gravar_itens(sessao: Session, rodada_id: int, itens: list[ItemRodada]) -> None:
    sessao.add_all(
        LinhaItemRodada(
            rodada_id=rodada_id,
            esperado_centavos=item.esperado_centavos,
            caiu_centavos=item.caiu_centavos,
            nao_caiu_centavos=item.nao_caiu_centavos,
            proximo_fechamento_centavos=item.proximo_fechamento_centavos,
            severidade=item.severidade.value if item.severidade else None,
            motivo=item.motivo.value if item.motivo else None,
            pendencia_centavos=item.pendencia_centavos,
            recebiveis=[_json(r) for r in item.recebiveis],
            creditos=[_json(c) for c in item.creditos],
        )
        for item in itens
    )
    sessao.flush()


def itens_da_rodada(sessao: Session, rodada_id: int) -> list[ItemRodada]:
    linhas = sessao.scalars(
        select(LinhaItemRodada).where(LinhaItemRodada.rodada_id == rodada_id).order_by(LinhaItemRodada.id)
    ).all()
    return [
        ItemRodada(
            recebiveis=[_recebivel_do_json(r) for r in l.recebiveis],
            creditos=[_lancamento_do_json(c) for c in l.creditos],
            esperado_centavos=l.esperado_centavos,
            caiu_centavos=l.caiu_centavos,
            nao_caiu_centavos=l.nao_caiu_centavos,
            proximo_fechamento_centavos=l.proximo_fechamento_centavos,
            severidade=Severidade(l.severidade) if l.severidade else None,
            motivo=Motivo(l.motivo) if l.motivo else None,
            pendencia_centavos=l.pendencia_centavos,
        )
        for l in linhas
    ]


def rodadas_com_recebivel(sessao: Session, cliente_id: str, recebivel_id: str) -> list[Rodada]:
    """Mesma ordem de `rodadas_do_cliente`. O filtro usa o índice GIN dos itens."""
    com_recebivel = select(LinhaItemRodada.rodada_id).where(
        LinhaItemRodada.recebiveis.contains([{"id": recebivel_id}])
    )
    linhas = sessao.scalars(
        select(LinhaRodada)
        .where(LinhaRodada.cliente_id == cliente_id, LinhaRodada.id.in_(com_recebivel))
        .order_by(LinhaRodada.criada_em.desc(), LinhaRodada.id.desc())
    ).all()
    return [_rodada(l) for l in linhas]


def _json(valor: Recebivel | Lancamento) -> dict[str, Any]:
    return {k: v.isoformat() if isinstance(v, date) else v for k, v in asdict(valor).items()}


def _recebivel_do_json(d: dict[str, Any]) -> Recebivel:
    return Recebivel(
        **d
        | {
            "vendido_em": date.fromisoformat(d["vendido_em"]),
            "liquidacao_prevista": date.fromisoformat(d["liquidacao_prevista"]),
        }
    )


def _lancamento_do_json(d: dict[str, Any]) -> Lancamento:
    return Lancamento(**d | {"lancado_em": datetime.fromisoformat(d["lancado_em"])})
