"""O formato das respostas HTTP. É daqui que sai o contrato TypeScript."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from fechamento import Lancamento, Motivo, Recebivel, Recomendacao, Severidade
from sinkfi.tipos import Papel


class _DeAtributos(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RodadaLida(_DeAtributos):
    id: int
    data_fechamento: date
    corte: datetime
    versao_regra: str
    criada_em: datetime


class ResumoLido(BaseModel):
    recomendacao: Recomendacao
    falta_de_verdade_centavos: int
    itens_falta_de_verdade: int
    itens_para_conferir: int
    # O limite usado no cálculo, lido agora. None = trava desligada.
    limite_trava_centavos: int | None


class ItemLido(_DeAtributos):
    """Um grupo de recebíveis, ou um crédito sozinho (sem recebíveis e sem valores de grupo)."""

    recebiveis: list[Recebivel]
    creditos: list[Lancamento]
    esperado_centavos: int | None
    caiu_centavos: int | None
    nao_caiu_centavos: int | None
    proximo_fechamento_centavos: int | None
    severidade: Severidade | None
    motivo: Motivo | None
    pendencia_centavos: int | None


class FechamentoResposta(BaseModel):
    rodada: RodadaLida
    resumo: ResumoLido
    itens: list[ItemLido]


class LoginEntrada(BaseModel):
    email: str
    senha: str


class EuResposta(BaseModel):
    email: str
    papel: Papel
    # None para o suporte, que não pertence a nenhum cliente.
    cliente_id: str | None


class LimiteEntrada(BaseModel):
    # None desliga a trava (ADR 0003).
    limite_trava_centavos: int | None = Field(ge=0)
