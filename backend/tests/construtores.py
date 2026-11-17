"""Constrói os tipos de entrada com o padrão dos CSVs.

Cada teste passa só os campos que importam para o caso.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fechamento import Lancamento, Loja, Recebivel

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
UTC = ZoneInfo("UTC")

# Segunda, 10/11, às 18:00 de São Paulo.
CORTE = datetime(2026, 11, 10, 18, 0, tzinfo=SAO_PAULO)

STONE = "16501555000100"
PAGSEGURO = "08561701000100"

LOJA_CENTRO = Loja(id="loja_centro", documento="10493827000160", adquirente="stone")
LOJA_SAVASSI = Loja(id="loja_savassi", documento="10493827000160", adquirente="pagseguro")
LOJAS = [LOJA_CENTRO, LOJA_SAVASSI]


def em_sao_paulo(mes: int, dia: int, hora: int = 12, minuto: int = 0, segundo: int = 0) -> datetime:
    return datetime(2026, mes, dia, hora, minuto, segundo, tzinfo=SAO_PAULO)


def recebivel(
    id: str,
    *,
    liquidacao_prevista: date,
    liquido_centavos: int,
    nsu: str,
    adquirente: str = "stone",
    loja_id: str = "loja_centro",
    trilho: str = "card",
    vendido_em: date = date(2026, 11, 1),
    parcela: int = 1,
    parcelas: int = 1,
    status: str = "open",
) -> Recebivel:
    return Recebivel(
        id=id,
        loja_id=loja_id,
        adquirente=adquirente,
        trilho=trilho,
        vendido_em=vendido_em,
        liquidacao_prevista=liquidacao_prevista,
        liquido_centavos=liquido_centavos,
        nsu=nsu,
        parcela=parcela,
        parcelas=parcelas,
        status=status,
    )


def lancamento(
    id: str,
    *,
    transacao_id: str,
    lancado_em: datetime,
    valor_centavos: int,
    descricao: str,
    documento_contraparte: str = STONE,
    tipo: str = "settlement",
    transacao_original_id: str | None = None,
) -> Lancamento:
    return Lancamento(
        id=id,
        transacao_id=transacao_id,
        transacao_original_id=transacao_original_id,
        lancado_em=lancado_em,
        valor_centavos=valor_centavos,
        documento_contraparte=documento_contraparte,
        descricao=descricao,
        tipo=tipo,
    )
