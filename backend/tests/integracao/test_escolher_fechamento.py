"""Escolher o fechamento (ADR 0007): a lista de semanas, a leitura e o pedido por corte, o término e o aviso.

Os cortes andam de 7 em 7 dias a partir da âncora da demonstração, terça 10/11 às 18:00.
Os CSVs têm dado até 10/11; o crédito de 12/11 leva o fechamento atual para 17/11.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sinkfi.api import app, obter_agora
from sinkfi.fila import obter_fila
from sinkfi.ingestao.ingerir import ingerir
from sinkfi.pedidos import processar_pedido
from sinkfi.rodadas import reprocessar, rodar_fechamento
from sinkfi.tipos import Rodada

from tests.construtores import CORTE, em_sao_paulo
from tests.integracao.cenarios import (
    LOJISTA_MARINA,
    MARINA,
    SUPORTE,
    FilaFalsa,
    criar_lojista,
    criar_suporte,
    dados_com_credito_a_mais,
    dados_com_credito_na_semana_seguinte,
    entrar,
    preparar_marina,
)

ANCORA = "2026-11-10T18:00:00-03:00"
CORTE_10 = CORTE
CORTE_17 = CORTE + timedelta(days=7)
# Terça, 17/11, depois do corte: a lista tem 10/11 e 17/11.
AGORA = em_sao_paulo(11, 17, 21)


@pytest.fixture(autouse=True)
def ancora(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SINKFI_ANCORA_DOS_CORTES", ANCORA)


@pytest.fixture
def fila() -> FilaFalsa:
    return FilaFalsa()


@pytest.fixture
def marina(sessao: Session, http: TestClient, fila: FilaFalsa) -> TestClient:
    """A Marina com os CSVs, logada como a lojista dela, às 21:00 de 17/11."""
    preparar_marina(sessao)
    criar_lojista(sessao, LOJISTA_MARINA, MARINA)
    app.dependency_overrides[obter_agora] = lambda: AGORA
    app.dependency_overrides[obter_fila] = lambda: fila
    entrar(http, LOJISTA_MARINA)
    return http


def _fechamento(http: TestClient, semana: str | None = None) -> dict:
    params = {"semana": semana} if semana else {}
    resposta = http.get(f"/clientes/{MARINA}/fechamento", params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _semanas(http: TestClient) -> dict[str, dict]:
    resposta = http.get(f"/clientes/{MARINA}/semanas")
    assert resposta.status_code == 200, resposta.text
    return {s["semana"]: s for s in resposta.json()}


def _terminei(http: TestClient, rodada: Rodada) -> None:
    resposta = http.post(f"/clientes/{MARINA}/terminei", json={"rodada_id": rodada.id})
    assert resposta.status_code == 201, resposta.text


# Fechamento atual


def test_fluxo_automatico_calcula_o_fechamento_atual(sessao: Session, tmp_path: Path):
    preparar_marina(sessao)
    ingerir(sessao, MARINA, dados_com_credito_na_semana_seguinte(tmp_path))

    # O pedido da ingestão não leva corte (#11). Em 24/11 o vigente é 24/11, mas o último com dado é 17/11.
    rodada = processar_pedido(sessao, MARINA, em_sao_paulo(11, 24, 21), ancora=datetime.fromisoformat(ANCORA))

    assert rodada.corte == CORTE_17


# Leitura e pedido


def test_fechamento_da_semana_devolve_a_rodada_mais_recente_daquela_semana(
    sessao: Session, marina: TestClient, tmp_path: Path
):
    rodar_fechamento(sessao, MARINA, CORTE_10)
    ingerir(sessao, MARINA, dados_com_credito_a_mais(tmp_path))
    nova = rodar_fechamento(sessao, MARINA, CORTE_10)
    rodar_fechamento(sessao, MARINA, CORTE_17)

    corpo = _fechamento(marina, "2026-11-10")

    assert corpo["rodada"]["id"] == nova.id
    assert corpo["resumo"]["itens_para_conferir"] == 3


def test_voltar_a_uma_semana_ja_calculada_mostra_a_rodada_dela(sessao: Session, marina: TestClient):
    da_10 = rodar_fechamento(sessao, MARINA, CORTE_10)
    da_17 = rodar_fechamento(sessao, MARINA, CORTE_17)
    # Mesmo hash: volta a rodada que já existia, que não é a criada por último.
    assert rodar_fechamento(sessao, MARINA, CORTE_10).id == da_10.id

    assert _fechamento(marina, "2026-11-10")["rodada"]["id"] == da_10.id
    assert _fechamento(marina, "2026-11-17")["rodada"]["id"] == da_17.id
    # Sem semana, o fechamento atual: com os CSVs, 10/11.
    assert _fechamento(marina)["rodada"]["id"] == da_10.id


def test_semana_sem_rodada_responde_404(sessao: Session, marina: TestClient):
    rodar_fechamento(sessao, MARINA, CORTE_10)

    resposta = marina.get(f"/clientes/{MARINA}/fechamento", params={"semana": "2026-11-17"})

    assert resposta.status_code == 404


def test_pedir_semana_enfileira_o_corte_daquela_semana(marina: TestClient, fila: FilaFalsa):
    resposta = marina.post(f"/clientes/{MARINA}/fechamentos", json={"semana": "2026-11-17"})

    assert resposta.status_code == 202
    assert fila.fechamentos_da_semana == [(MARINA, CORTE_17)]


def test_pedir_semana_fora_da_lista_responde_422(marina: TestClient, fila: FilaFalsa):
    # 24/11 ainda não passou; 11/11 não é corte.
    for semana in ["2026-11-24", "2026-11-11"]:
        resposta = marina.post(f"/clientes/{MARINA}/fechamentos", json={"semana": semana})
        assert resposta.status_code == 422, semana

    assert fila.fechamentos_da_semana == []


def test_reprocessar_vale_para_a_semana_pedida(
    sessao: Session, marina: TestClient, fila: FilaFalsa, tmp_path: Path
):
    da_10 = rodar_fechamento(sessao, MARINA, CORTE_10)
    da_17 = rodar_fechamento(sessao, MARINA, CORTE_17)
    criar_suporte(sessao)
    entrar(marina, SUPORTE)

    resposta = marina.post(f"/clientes/{MARINA}/reprocessar", json={"semana": "2026-11-10"})

    assert resposta.status_code == 202
    assert fila.reprocessamentos == [(MARINA, CORTE_10)]

    # O que o worker faz com o pedido, depois de chegar dado novo.
    ingerir(sessao, MARINA, dados_com_credito_a_mais(tmp_path))
    nova = reprocessar(sessao, *fila.reprocessamentos[0])

    assert nova.id != da_10.id
    assert _fechamento(marina, "2026-11-10")["rodada"]["id"] == nova.id
    assert _fechamento(marina, "2026-11-17")["rodada"]["id"] == da_17.id


# Término e aviso


@pytest.fixture
def anterior_com_rodada(sessao: Session, marina: TestClient, tmp_path: Path) -> Rodada:
    """10/11 calculado; depois chega um crédito de 12/11 e o fechamento atual passa a ser 17/11, sem rodada."""
    rodada = rodar_fechamento(sessao, MARINA, CORTE_10)
    ingerir(sessao, MARINA, dados_com_credito_na_semana_seguinte(tmp_path))
    return rodada


def test_termino_vale_em_fechamento_anterior(
    sessao: Session, marina: TestClient, anterior_com_rodada: Rodada
):
    da_17 = rodar_fechamento(sessao, MARINA, CORTE_17)

    _terminei(marina, anterior_com_rodada)

    assert _fechamento(marina, "2026-11-10")["ultimo_termino"]["rodada_id"] == anterior_com_rodada.id
    # O término de 10/11 não aparece no fechamento de 17/11.
    assert _fechamento(marina, "2026-11-17")["rodada"]["id"] == da_17.id
    assert _fechamento(marina, "2026-11-17")["ultimo_termino"] is None


def test_aviso_mostra_fechamento_anterior_com_pendencia_e_sem_termino(
    marina: TestClient, anterior_com_rodada: Rodada
):
    semanas = _semanas(marina)

    assert semanas["2026-11-10"] == {
        "semana": "2026-11-10",
        "corte": "2026-11-10T18:00:00-03:00",
        "atual": False,
        "tem_rodada": True,
        "itens_falta_de_verdade": 5,
        "itens_para_conferir": 2,
        "terminado": False,
        "aviso": True,
    }
    assert semanas["2026-11-17"]["atual"] is True
    assert semanas["2026-11-17"]["aviso"] is False


def test_termino_no_fechamento_anterior_tira_ele_do_aviso(
    marina: TestClient, anterior_com_rodada: Rodada
):
    _terminei(marina, anterior_com_rodada)

    semana = _semanas(marina)["2026-11-10"]

    assert semana["terminado"] is True
    assert semana["aviso"] is False


def test_fechamento_sem_rodada_nao_entra_no_aviso(marina: TestClient, sessao: Session, tmp_path: Path):
    # 10/11 tem pendências no dado, mas nunca foi calculado.
    ingerir(sessao, MARINA, dados_com_credito_na_semana_seguinte(tmp_path))

    semana = _semanas(marina)["2026-11-10"]

    assert semana["tem_rodada"] is False
    assert semana["aviso"] is False
