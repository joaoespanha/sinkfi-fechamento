"""A atualização dos dados (ADR 0011): quando foi a última ingestão e quando vem a próxima.

A agenda é 0, 6, 12 e 18h UTC; em São Paulo (UTC-3), 21h, 3h, 9h e 15h.
"""

from datetime import timedelta

from sinkfi.atualizacao import atualizacao, proxima_prevista

from tests.construtores import em_sao_paulo

# Próxima prevista


def test_antes_de_uma_hora_da_agenda_a_proxima_e_ela():
    assert proxima_prevista(em_sao_paulo(11, 18, 14, 59)) == em_sao_paulo(11, 18, 15)


def test_em_cima_da_hora_da_agenda_a_proxima_e_a_seguinte():
    # A das 15:00 está rodando ou acabou de rodar: a próxima é a das 21:00.
    assert proxima_prevista(em_sao_paulo(11, 18, 15)) == em_sao_paulo(11, 18, 21)


def test_depois_de_uma_hora_da_agenda_a_proxima_e_a_seguinte():
    assert proxima_prevista(em_sao_paulo(11, 18, 15, 1)) == em_sao_paulo(11, 18, 21)


def test_depois_da_ultima_do_dia_a_proxima_e_no_dia_seguinte():
    # 21:30 em São Paulo já é 19/11 em UTC; a próxima é 03:00 de 19/11.
    assert proxima_prevista(em_sao_paulo(11, 18, 21, 30)) == em_sao_paulo(11, 19, 3)


# Atualização


def test_com_ingestao_recente_nao_esta_atrasada():
    ultima = em_sao_paulo(11, 18, 15, 0, 5)

    lida = atualizacao(ultima, agora=em_sao_paulo(11, 18, 17))

    assert lida.ultima_em == ultima
    assert lida.proxima_prevista_em == em_sao_paulo(11, 18, 21)
    assert lida.atrasada is False
    assert lida.primeira_perdida_em is None


def test_doze_horas_ainda_nao_e_atraso():
    # Um ciclo perdido pode ser só o worker fora: a próxima cobre.
    ultima = em_sao_paulo(11, 17, 15)

    lida = atualizacao(ultima, agora=ultima + timedelta(hours=12))

    assert lida.atrasada is False


def test_mais_de_doze_horas_esta_atrasada_e_nomeia_a_primeira_perdida():
    ultima = em_sao_paulo(11, 17, 15, 0, 5)

    lida = atualizacao(ultima, agora=em_sao_paulo(11, 18, 3, 1))

    assert lida.atrasada is True
    assert lida.primeira_perdida_em == em_sao_paulo(11, 17, 21)
    assert lida.proxima_prevista_em == em_sao_paulo(11, 18, 9)


def test_sem_ingestao_mostra_so_a_proxima():
    lida = atualizacao(None, agora=em_sao_paulo(11, 18, 17))

    assert lida.ultima_em is None
    assert lida.proxima_prevista_em == em_sao_paulo(11, 18, 21)
    assert lida.atrasada is False
    assert lida.primeira_perdida_em is None
