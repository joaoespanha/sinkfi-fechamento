"""Leitura e gravação no Postgres. Recebe e devolve tipos do núcleo e de `sinkfi.tipos`."""

from dataclasses import asdict
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from fechamento import Lancamento, Loja, Motivo, Recebivel, Recomendacao, Resumo, Severidade
from sinkfi.banco.modelos import (
    LinhaCliente,
    LinhaItemRodada,
    LinhaLancamento,
    LinhaLoja,
    LinhaMudancaLimite,
    LinhaRecebivel,
    LinhaRodada,
    LinhaTermino,
    LinhaUsuario,
)
from sinkfi.tipos import ConfigFechamento, Entrada, ItemRodada, MudancaLimite, Papel, Rodada, Termino, Usuario


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


def definir_limite(sessao: Session, cliente_id: str, limite_trava_centavos: int | None) -> None:
    """None desliga a trava (ADR 0003)."""
    sessao.get_one(LinhaCliente, cliente_id).limite_trava_centavos = limite_trava_centavos
    sessao.flush()


def limite_do_cliente(sessao: Session, cliente_id: str) -> int | None:
    return sessao.get_one(LinhaCliente, cliente_id).limite_trava_centavos


def config_do_cliente(sessao: Session, cliente_id: str) -> ConfigFechamento | None:
    linha = sessao.get(LinhaCliente, cliente_id)
    if linha is None:
        return None
    return ConfigFechamento(dia_fechamento=linha.dia_fechamento, hora_corte=linha.hora_corte, fuso=linha.fuso)


def ids_dos_clientes(sessao: Session) -> list[str]:
    return list(sessao.scalars(select(LinhaCliente.id).order_by(LinhaCliente.id)))


def cliente_existe(sessao: Session, id: str) -> bool:
    return sessao.get(LinhaCliente, id) is not None


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
        criada_em=linha.criada_em,
    )


def rodada_do_cliente(sessao: Session, cliente_id: str, rodada_id: int) -> Rodada | None:
    """None quando a rodada não existe ou é de outro cliente."""
    linha = sessao.get(LinhaRodada, rodada_id)
    return _rodada(linha) if linha and linha.cliente_id == cliente_id else None


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


def gravar_usuario(
    sessao: Session, *, email: str, senha_hash: str, papel: Papel, cliente_id: str | None
) -> Usuario:
    linha = LinhaUsuario(email=email, senha_hash=senha_hash, papel=papel.value, cliente_id=cliente_id, ativo=True)
    sessao.add(linha)
    sessao.flush()
    return _usuario(linha)


def usuario_por_id(sessao: Session, id: int) -> Usuario | None:
    linha = sessao.get(LinhaUsuario, id)
    return _usuario(linha) if linha else None


def usuario_e_hash_por_email(sessao: Session, email: str) -> tuple[Usuario, str] | None:
    linha = sessao.scalars(select(LinhaUsuario).where(LinhaUsuario.email == email)).one_or_none()
    return (_usuario(linha), linha.senha_hash) if linha else None


def desativar_usuario(sessao: Session, email: str) -> None:
    sessao.scalars(select(LinhaUsuario).where(LinhaUsuario.email == email)).one().ativo = False
    sessao.flush()


def _usuario(linha: LinhaUsuario) -> Usuario:
    return Usuario(
        id=linha.id,
        email=linha.email,
        papel=Papel(linha.papel),
        cliente_id=linha.cliente_id,
        ativo=linha.ativo,
    )


def gravar_mudanca_limite(
    sessao: Session, *, cliente_id: str, usuario_id: int, em: datetime, de: int | None, para: int | None
) -> None:
    sessao.add(
        LinhaMudancaLimite(
            cliente_id=cliente_id, usuario_id=usuario_id, em=em, de_centavos=de, para_centavos=para
        )
    )
    sessao.flush()


def mudancas_de_limite(sessao: Session, cliente_id: str) -> list[MudancaLimite]:
    """Da mais antiga para a mais nova."""
    linhas = sessao.execute(
        select(LinhaMudancaLimite, LinhaUsuario.email)
        .join(LinhaUsuario, LinhaUsuario.id == LinhaMudancaLimite.usuario_id)
        .where(LinhaMudancaLimite.cliente_id == cliente_id)
        .order_by(LinhaMudancaLimite.id)
    ).all()
    return [
        MudancaLimite(quem=email, em=m.em, de_centavos=m.de_centavos, para_centavos=m.para_centavos)
        for m, email in linhas
    ]


def gravar_termino(
    sessao: Session,
    *,
    cliente_id: str,
    usuario_id: int,
    em: datetime,
    rodada_id: int,
    limite_trava_centavos: int | None,
    resumo: Resumo,
) -> None:
    sessao.add(
        LinhaTermino(
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            em=em,
            rodada_id=rodada_id,
            limite_trava_centavos=limite_trava_centavos,
            resumo=asdict(resumo) | {"recomendacao": resumo.recomendacao.value},
        )
    )
    sessao.flush()


def terminos_do_cliente(sessao: Session, cliente_id: str) -> list[Termino]:
    """Do mais antigo para o mais novo."""
    linhas = sessao.execute(
        select(LinhaTermino, LinhaUsuario.email)
        .join(LinhaUsuario, LinhaUsuario.id == LinhaTermino.usuario_id)
        .where(LinhaTermino.cliente_id == cliente_id)
        .order_by(LinhaTermino.id)
    ).all()
    return [
        Termino(
            quem=email,
            em=t.em,
            rodada_id=t.rodada_id,
            limite_trava_centavos=t.limite_trava_centavos,
            resumo=Resumo(**t.resumo | {"recomendacao": Recomendacao(t.resumo["recomendacao"])}),
        )
        for t, email in linhas
    ]
