"""A atualização dos dados (ADR 0011): a ingestão grava a hora e o fechamento a devolve com a próxima prevista."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sinkfi.banco import repositorios
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.rodadas import rodar_fechamento

from tests.construtores import CORTE
from tests.integracao.cenarios import DADOS, LOJISTA_MARINA, MARINA, criar_lojista, entrar, preparar_marina


def _criar_marina_sem_dados(sessao: Session) -> None:
    repositorios.criar_cliente(
        sessao, id=MARINA, nome="Marina", dia_fechamento=1, hora_corte=time(18, 0), fuso="America/Sao_Paulo"
    )


def test_cliente_sem_ingestao_nao_tem_hora(sessao: Session):
    _criar_marina_sem_dados(sessao)

    assert repositorios.ultima_ingestao_do_cliente(sessao, MARINA) is None


def test_ingestao_grava_a_hora_da_ultima_ingestao(sessao: Session):
    _criar_marina_sem_dados(sessao)

    ingerir(sessao, MARINA, DADOS)

    assert repositorios.ultima_ingestao_do_cliente(sessao, MARINA) is not None


def test_ingestao_desfeita_nao_conta_como_atualizacao(sessao: Session):
    # "Atualizado" é a última ingestão que deu certo: a hora entra na transação do dado.
    _criar_marina_sem_dados(sessao)

    ingestao = sessao.begin_nested()
    ingerir(sessao, MARINA, DADOS)
    ingestao.rollback()

    assert repositorios.ultima_ingestao_do_cliente(sessao, MARINA) is None


def test_fechamento_devolve_a_ultima_ingestao_e_a_proxima_prevista(sessao: Session, http: TestClient):
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    entrar(http, LOJISTA_MARINA)
    rodar_fechamento(sessao, MARINA, CORTE)
    ultima = repositorios.ultima_ingestao_do_cliente(sessao, MARINA)

    resposta = http.get(f"/clientes/{MARINA}/fechamento")

    assert resposta.status_code == 200
    atualizacao = resposta.json()["atualizacao"]
    assert datetime.fromisoformat(atualizacao["ultima_em"]) == ultima
    # A api vê 17/11 às 21:00 de São Paulo, em cima da hora da agenda: a próxima é a das 03:00.
    assert datetime.fromisoformat(atualizacao["proxima_prevista_em"]) == datetime(
        2026, 11, 18, 3, 0, tzinfo=ZoneInfo("America/Sao_Paulo")
    )
    assert atualizacao["atrasada"] is False
    assert atualizacao["primeira_perdida_em"] is None
