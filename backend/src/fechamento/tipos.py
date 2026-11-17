from dataclasses import dataclass, field
from datetime import date, datetime


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
    liquidacao_prevista: date
    liquido_centavos: int
    nsu: str
    parcela: int
    parcelas: int
    status: str


@dataclass(frozen=True)
class Lancamento:
    id: str
    transacao_id: str
    lancado_em: datetime
    valor_centavos: int
    documento_contraparte: str
    descricao: str
    tipo: str


@dataclass(frozen=True)
class GrupoDeRecebiveis:
    recebiveis: list[Recebivel]
    creditos: list[Lancamento]
    esperado_centavos: int
    caiu_centavos: int
    nao_caiu_centavos: int
    proximo_fechamento_centavos: int


@dataclass(frozen=True)
class Fechamento:
    grupos: list[GrupoDeRecebiveis]
    pendencias: list = field(default_factory=list)
