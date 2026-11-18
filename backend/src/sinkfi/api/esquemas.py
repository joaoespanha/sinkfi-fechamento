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
    # O dia da semana em que o item aparece (#26). None = antes desta semana.
    dia: date | None


class TerminoLido(BaseModel):
    """Um "Terminei": quem, quando, a rodada vista e o resumo daquele momento (com o limite de então)."""

    quem: str
    em: datetime
    rodada_id: int
    limite_trava_centavos: int | None
    resumo: ResumoLido


class FechamentoResposta(BaseModel):
    rodada: RodadaLida
    resumo: ResumoLido
    itens: list[ItemLido]
    # Se a rodada dele não é a mostrada, chegou fechamento novo depois do "Terminei".
    ultimo_termino: TerminoLido | None


class TermineiEntrada(BaseModel):
    # A rodada que a tela está mostrando, não a mais recente do banco: pode ter chegado outra no meio.
    rodada_id: int


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


class LimiteLido(BaseModel):
    # None = trava desligada.
    limite_trava_centavos: int | None


class SemanaLida(BaseModel):
    """Um fechamento da lista (ADR 0007). As contagens são da rodada mais recente; None sem rodada."""

    semana: date
    corte: datetime
    atual: bool
    tem_rodada: bool
    itens_falta_de_verdade: int | None
    itens_para_conferir: int | None
    terminado: bool
    # Anterior ao atual, com pendência e sem "Terminei" na rodada mais recente.
    aviso: bool


class SemanaEntrada(BaseModel):
    # A data do corte, como vem em `SemanaLida.semana`.
    semana: date


class OperacaoLida(BaseModel):
    """A saúde da fila (Monitorar): o que ficou parado sem chegar ao fechamento."""

    pedidos_parados: int = Field(
        description="Pedidos de fechamento gravados que o relay do outbox ainda não publicou."
    )
    idade_do_mais_antigo_segundos: int | None = Field(
        description="Há quanto tempo o mais antigo espera. Sem pedido parado, null."
    )
    mensagens_na_dead_letter: int | None = Field(
        description="Mensagens em `fechamento.morta`: fechamentos que falharam de vez. Com o RabbitMQ fora do ar, null."
    )
