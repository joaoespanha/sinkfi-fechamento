"""Dados de demonstração: `python -m sinkfi.semear`.

Cria a Marina, ingere os CSVs e roda o fechamento do enunciado. Rodar de novo não
repete nada: o cliente só é criado uma vez, a ingestão é upsert e a rodada com a
mesma entrada já existe. Em produção o cliente nasce por cadastro e a ingestão
chega pela api; este módulo não faz parte desse caminho.
"""

import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.rodadas import rodar_fechamento

MARINA = "cli_marina"
SAO_PAULO = "America/Sao_Paulo"
# O corte do enunciado, passado direto em vez de vir de `fechamento_vigente`:
# o enunciado chama 10/11/2026 de segunda, mas é terça, e é nessa data que os CSVs batem.
CORTE_DO_ENUNCIADO = datetime(2026, 11, 10, 18, 0, tzinfo=ZoneInfo(SAO_PAULO))


def semear(sessao: Session, pasta: Path) -> None:
    if not repositorios.cliente_existe(sessao, MARINA):
        repositorios.criar_cliente(
            sessao,
            id=MARINA,
            nome="Marina",
            dia_fechamento=1,
            hora_corte=time(18, 0),
            fuso=SAO_PAULO,
        )
    ingerir(sessao, MARINA, pasta)
    rodar_fechamento(sessao, MARINA, CORTE_DO_ENUNCIADO)


if __name__ == "__main__":
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as sessao, sessao.begin():
        semear(sessao, Path(os.environ.get("PASTA_DADOS", "dados")))
