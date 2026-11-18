from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

# O recebível pela adquirente e pelo id: o id sozinho pode ser de duas adquirentes (ADR 0009).
Identidade = tuple[str, str]


@dataclass(frozen=True)
class Loja:
    id: str
    documento: str
    adquirente: str


@dataclass(frozen=True)
class Recebivel:
    id: str
    loja_id: str
    adquirente: str
    trilho: str
    vendido_em: date
    liquidacao_prevista: date
    liquido_centavos: int
    nsu: str
    parcela: int
    parcelas: int
    status: str

    @property
    def identidade(self) -> Identidade:
        """O id vem da adquirente: duas adquirentes podem usar o mesmo (ADR 0009)."""
        return (self.adquirente, self.id)


@dataclass(frozen=True)
class Lancamento:
    id: str
    transacao_id: str
    transacao_original_id: str | None
    lancado_em: datetime
    valor_centavos: int
    documento_contraparte: str
    descricao: str
    tipo: str
    # `pending` não é dinheiro na conta (README). O padrão lê o JSON de rodadas gravadas antes do campo.
    status: str = "confirmed"


@dataclass(frozen=True)
class GrupoDeRecebiveis:
    recebiveis: list[Recebivel]
    creditos: list[Lancamento]
    esperado_centavos: int
    caiu_centavos: int
    nao_caiu_centavos: int
    proximo_fechamento_centavos: int

    @property
    def entre_lojas(self) -> bool:
        return len({r.loja_id for r in self.recebiveis}) > 1


class Severidade(Enum):
    FALTA_DE_VERDADE = "falta_de_verdade"
    PARA_CONFERIR = "para_conferir"


class Motivo(Enum):
    NAO_CAIU = "nao_caiu"
    CAIU_EM_PARTE = "caiu_em_parte"
    GRUPO_NAO_FECHA = "grupo_nao_fecha"
    CHARGEBACK = "chargeback"
    VENDA_CANCELADA = "venda_cancelada"
    ENTRADA_SEM_RECEBIVEL = "entrada_sem_recebivel"
    PODE_SER_ANTECIPACAO = "pode_ser_antecipacao"
    CAIU_A_MAIS = "caiu_a_mais"


@dataclass(frozen=True)
class Pendencia:
    severidade: Severidade
    motivo: Motivo
    valor_centavos: int
    grupo: GrupoDeRecebiveis | None = None
    lancamento: Lancamento | None = None


@dataclass(frozen=True)
class Fechamento:
    grupos: list[GrupoDeRecebiveis]
    pendencias: list[Pendencia] = field(default_factory=list)


class Recomendacao(Enum):
    PODE_FECHAR = "pode_fechar"
    FALTAM = "faltam"
    NAO_FECHE = "nao_feche"


@dataclass(frozen=True)
class Resumo:
    recomendacao: Recomendacao
    falta_de_verdade_centavos: int
    itens_falta_de_verdade: int
    itens_para_conferir: int
