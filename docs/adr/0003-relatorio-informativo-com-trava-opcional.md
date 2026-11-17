# Relatório informativo, com trava opcional por valor

Status: aceito, 16/11/2026

O fechamento é um relatório e nunca impede a lojista de fechar. Ele diz o que ela pode fechar e o que é falta de verdade, e quem decide é ela. A trava é um limite opcional que ela define sobre a soma das faltas de verdade. Vem desligada, e acima do limite só muda o texto do resumo.

## Contexto

O enunciado diz que ninguém definiu a partir de qual diferença o fechamento trava. A Marina pede informação ("me fala o que eu posso fechar e o que está faltando de verdade"), não um bloqueio. Lemos "travar" como recomendar não fechar.

## Alternativas recusadas

- **Bloquear o fechamento acima de uma diferença.** Exigiria uma ação de fechar e uma política de materialidade que ninguém definiu. Inventar essa política seria decidir pela lojista.
- **Travar por quantidade de pendências.** Uma falta de 4.775,00 pesa mais que cinco de 44,33.
- **Somar faltas com sobras.** Os 4.775,00 que não caíram do rec_7001 e os 3.152,00 que caíram da venda cancelada T-2009 dariam 1.623,00. A soma é absoluta: 7.927,00.

## Consequências

- Cada pendência é falta de verdade ou para conferir, e só a falta de verdade entra na soma da trava. Próximo fechamento não é pendência.
- A regra é pura: (pendências, limite) → resumo. Não existe estado de "semana fechada".
- Sem uma ação de fechar, o monitoramento perde o sinal direto de que a lojista terminou. Esse sinal (um botão "Terminei" que só registra o momento, ou um sinal indireto) se decide na seção Monitorar do `DECISOES.md`.

## Testes que garantem

- `resumo_sem_falta_de_verdade_diz_pode_fechar`
- `resumo_com_falta_de_verdade_mostra_total_e_quantidade`
- `trava_desligada_por_padrao_nunca_trava`
- `trava_soma_faltas_sem_compensar_sobra`
- `trava_ignora_itens_para_conferir`
- `falta_abaixo_do_limite_resumo_pode_fechar`
- `falta_acima_do_limite_resumo_nao_feche`
- `venda_cancelada_com_credito_e_falta_de_verdade`
