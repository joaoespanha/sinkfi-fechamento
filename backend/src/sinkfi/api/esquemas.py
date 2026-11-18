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


class ConferenciaLida(BaseModel):
    """Uma conferência: quem, quando, a rodada vista e o resumo daquele momento (com o limite de então)."""

    quem: str
    em: datetime
    rodada_id: int
    limite_trava_centavos: int | None
    resumo: ResumoLido


class AtualizacaoLida(_DeAtributos):
    """Até quando os números estão atualizados e quando vem a próxima ingestão (ADR 0011)."""

    ultima_em: datetime | None = Field(
        description="A última ingestão que deu certo, com ou sem dado novo. Sem ingestão, null."
    )
    proxima_prevista_em: datetime = Field(
        description="A próxima hora da agenda. Prevista: a que vence com o worker fora não roda, e a seguinte cobre."
    )
    atrasada: bool = Field(description="A última ingestão tem mais de 12 h (dois ciclos).")
    primeira_perdida_em: datetime | None = Field(
        description="Só quando atrasada: a primeira hora da agenda depois da última ingestão, que não aconteceu."
    )


class FechamentoResposta(BaseModel):
    rodada: RodadaLida
    resumo: ResumoLido
    itens: list[ItemLido]
    # Se a rodada dela não é a mostrada, chegou fechamento novo depois da conferência.
    ultima_conferencia: ConferenciaLida | None
    atualizacao: AtualizacaoLida


class ConferenciaEntrada(BaseModel):
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
    conferido: bool
    # Anterior ao atual, com pendência e sem conferência na rodada mais recente.
    aviso: bool


class SemanaEntrada(BaseModel):
    # A data do corte, como vem em `SemanaLida.semana`.
    semana: date


class OperacaoLida(BaseModel):
    """A saúde da fila e da ingestão (Monitorar): o que ficou parado sem chegar ao fechamento."""

    pedidos_pendentes: int = Field(
        description="Pedidos de fechamento gravados que o relay do outbox ainda não publicou."
    )
    idade_do_mais_antigo_segundos: int | None = Field(
        description="Há quanto tempo o mais antigo espera, pelo relógio do banco. Sem pedido pendente, null."
    )
    mensagens_na_dead_letter: int | None = Field(
        description=(
            "Mensagens em `fechamento.morta`: ingestões e fechamentos que falharam de vez."
            " Com o RabbitMQ fora do ar ou recusando o login, null."
        )
    )
    ultima_ingestao_em: datetime | None = Field(
        description=(
            "A ingestão mais recente de qualquer cliente: o pulso do beat, que agenda as ingestões."
            " Velha para todos ao mesmo tempo, o beat parou. Sem nenhuma ingestão, null."
        )
    )
    clientes_com_ingestao_atrasada: list[str] = Field(
        description=(
            "Ids dos clientes sem ingestão há mais de 12 h, a mesma regra do \"atrasada\" da tela (ADR 0011)."
            " Cliente que nunca teve ingestão não entra."
        )
    )


class LojaEncontradaLida(_DeAtributos):
    nome: str
    documento: str = Field(description="CNPJ só com dígitos.")


class ClienteEncontradoLido(_DeAtributos):
    """Um resultado da busca do suporte (ADR 0010)."""

    id: str
    nome: str
    lojas: list[LojaEncontradaLida]
