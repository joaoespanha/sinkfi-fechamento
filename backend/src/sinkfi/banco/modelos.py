"""Tabelas do banco. Só `repositorios.py` e as migrações importam este módulo.

As tabelas de entrada guardam todas as colunas dos CSVs, mesmo as que a regra não usa:
a ingestão não decide o que a próxima versão da regra vai precisar.
"""

from datetime import date, datetime, time

from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Identity, Index, SmallInteger, Text, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LinhaCliente(Base):
    __tablename__ = "clientes"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    nome: Mapped[str] = mapped_column(Text)
    # Dia da semana do fechamento, como `isoweekday`: 1 = segunda, 7 = domingo.
    dia_fechamento: Mapped[int] = mapped_column(SmallInteger)
    hora_corte: Mapped[time] = mapped_column(Time)
    fuso: Mapped[str] = mapped_column(Text)
    # NULL = trava desligada (ADR 0003).
    limite_trava_centavos: Mapped[int | None] = mapped_column(BigInteger)


class LinhaLoja(Base):
    __tablename__ = "lojas"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"))
    nome: Mapped[str] = mapped_column(Text)
    documento: Mapped[str] = mapped_column(Text)
    adquirente: Mapped[str] = mapped_column(Text)


class LinhaRecebivel(Base):
    __tablename__ = "recebiveis"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    loja_id: Mapped[str] = mapped_column(ForeignKey("lojas.id"))
    adquirente: Mapped[str] = mapped_column(Text)
    trilho: Mapped[str] = mapped_column(Text)
    vendido_em: Mapped[date] = mapped_column(Date)
    liquidacao_prevista: Mapped[date] = mapped_column(Date)
    bruto_centavos: Mapped[int] = mapped_column(BigInteger)
    mdr_centavos: Mapped[int] = mapped_column(BigInteger)
    antecipacao_centavos: Mapped[int] = mapped_column(BigInteger)
    liquido_centavos: Mapped[int] = mapped_column(BigInteger)
    nsu: Mapped[str] = mapped_column(Text)
    parcela: Mapped[int] = mapped_column(SmallInteger)
    parcelas: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(Text)


class LinhaLancamento(Base):
    __tablename__ = "lancamentos"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"))
    transacao_id: Mapped[str] = mapped_column(Text)
    transacao_original_id: Mapped[str | None] = mapped_column(Text)
    lancado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valor_centavos: Mapped[int] = mapped_column(BigInteger)
    nome_contraparte: Mapped[str] = mapped_column(Text)
    documento_contraparte: Mapped[str] = mapped_column(Text)
    descricao: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(Text)


class LinhaRodada(Base):
    __tablename__ = "rodadas"
    __table_args__ = (UniqueConstraint("cliente_id", "data_fechamento", "hash_entrada"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"))
    data_fechamento: Mapped[date] = mapped_column(Date)
    corte: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    versao_regra: Mapped[str] = mapped_column(Text)
    hash_entrada: Mapped[str] = mapped_column(Text)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LinhaItemRodada(Base):
    """Recebíveis e créditos em JSONB, como estavam na hora do cálculo (ADR 0006)."""

    __tablename__ = "itens_rodada"
    __table_args__ = (
        Index("ix_itens_rodada_recebiveis", "recebiveis", postgresql_using="gin", postgresql_ops={"recebiveis": "jsonb_path_ops"}),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    rodada_id: Mapped[int] = mapped_column(ForeignKey("rodadas.id"), index=True)
    # NULL nos itens de crédito, que não têm grupo.
    esperado_centavos: Mapped[int | None] = mapped_column(BigInteger)
    caiu_centavos: Mapped[int | None] = mapped_column(BigInteger)
    nao_caiu_centavos: Mapped[int | None] = mapped_column(BigInteger)
    proximo_fechamento_centavos: Mapped[int | None] = mapped_column(BigInteger)
    # NULL quando o item não é pendência.
    severidade: Mapped[str | None] = mapped_column(Text)
    motivo: Mapped[str | None] = mapped_column(Text)
    pendencia_centavos: Mapped[int | None] = mapped_column(BigInteger)
    recebiveis: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    creditos: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)


class LinhaUsuario(Base):
    """A lojista tem cliente; o suporte não (ADR 0005). O CHECK fica no banco."""

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "(papel = 'lojista' AND cliente_id IS NOT NULL)"
            " OR (papel = 'suporte' AND cliente_id IS NULL)",
            name="ck_usuarios_papel_e_cliente",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True)
    senha_hash: Mapped[str] = mapped_column(Text)
    papel: Mapped[str] = mapped_column(Text)
    cliente_id: Mapped[str | None] = mapped_column(ForeignKey("clientes.id"))
    ativo: Mapped[bool] = mapped_column(Boolean, server_default="true")


class LinhaMudancaLimite(Base):
    """Só inserção (#12). NULL em `de`/`para` = trava desligada."""

    __tablename__ = "mudancas_limite"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    de_centavos: Mapped[int | None] = mapped_column(BigInteger)
    para_centavos: Mapped[int | None] = mapped_column(BigInteger)


class LinhaTermino(Base):
    """Só inserção (#12): cada "Terminei" com a rodada vista, o limite e o resumo do momento."""

    __tablename__ = "terminos"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rodada_id: Mapped[int] = mapped_column(ForeignKey("rodadas.id"))
    limite_trava_centavos: Mapped[int | None] = mapped_column(BigInteger)
    resumo: Mapped[dict[str, Any]] = mapped_column(JSONB)
