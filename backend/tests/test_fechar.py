from datetime import date, datetime
from zoneinfo import ZoneInfo

from fechamento import Lancamento, Loja, Recebivel, fechar

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
UTC = ZoneInfo("UTC")
CORTE = datetime(2026, 11, 10, 18, 0, tzinfo=SAO_PAULO)

PAGSEGURO = "08561701000100"

LOJA_SAVASSI = Loja(
    id="loja_savassi",
    documento="10493827000160",
    adquirente="pagseguro",
)


def test_credito_depois_do_corte_vai_para_proximo_fechamento():
    rec_7002 = Recebivel(
        id="rec_7002",
        loja_id="loja_savassi",
        adquirente="pagseguro",
        liquidacao_prevista=date(2026, 11, 10),
        liquido_centavos=64000,
        nsu="PAG-7002",
        parcela=1,
        parcelas=1,
        status="open",
    )
    # 21:40Z é 18:40 em São Paulo: caiu 40 minutos depois do corte.
    t_7002 = Lancamento(
        id="ext_13",
        transacao_id="T-7002",
        lancado_em=datetime(2026, 11, 10, 21, 40, tzinfo=UTC),
        valor_centavos=64000,
        documento_contraparte=PAGSEGURO,
        descricao="PAG-7002",
        tipo="settlement",
    )

    fechamento = fechar(
        recebiveis=[rec_7002],
        lancamentos=[t_7002],
        lojas=[LOJA_SAVASSI],
        corte=CORTE,
    )

    [grupo] = fechamento.grupos
    assert grupo.esperado_centavos == 64000
    assert grupo.proximo_fechamento_centavos == 64000
    assert grupo.caiu_centavos == 0
    assert grupo.nao_caiu_centavos == 0
    assert fechamento.pendencias == []
