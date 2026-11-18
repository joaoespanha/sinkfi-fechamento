# Escolher o fechamento: só o corte, a tela abre no atual e o pedido manual leva o corte

Status: aceito, 17/11/2026

A lojista e o suporte escolhem qual fechamento ver, entre os cortes que já passaram. Escolher é só dizer o corte: a regra é acumulada e não tem data de início, então não existe "de quando". A tela abre no fechamento atual, o mais recente com dado. Um fechamento sem rodada é calculado pela fila, num pedido que leva o corte; o pedido da ingestão continua sem corte.

## Contexto

Até aqui a tela mostrava só a rodada criada por último, e a demonstração fixava o corte em 10/11 com o `SINKFI_CORTE_FIXO`. Não dava para ver um fechamento anterior, nem dados novos de outra semana. E, com várias semanas, "a rodada criada por último" deixa de servir: voltar a um corte já calculado devolve a rodada existente pelo hash (ADR 0006), que não é a mais nova, e a tela continuaria na outra semana.

## Decisões

- **Só o corte.** Um fechamento "de 03/11 a 10/11" esconderia uma falta de três semanas atrás, que continua sendo falta.
- **Só cortes que já passaram**, pelo relógio no fuso do cliente. Num corte futuro, o recebível que ainda não venceu apareceria como falta: isso é previsão, outro produto.
- **Fechamento atual: o mais recente com dado.** O último corte que passou com algum recebível previsto ou crédito nos dias dele. A api e o worker usam a mesma função. Em produção, com dado chegando todo dia, ele coincide com o fechamento vigente.
- **Foto, não recálculo.** Um fechamento já calculado mostra a sua rodada mais recente. Só o atual recebe rodada nova da ingestão; um anterior só muda com "Reprocessar".
- **Pedido manual com corte.** O pedido da ingestão continua sem corte (#11): o worker calcula o fechamento atual na hora. O pedido de quem escolheu um fechamento, e o "Reprocessar", levam o corte.
- **Âncora dos cortes na demonstração.** Os CSVs batem com o corte de terça, 10/11, e a Marina fecha na segunda. `SINKFI_ANCORA_DOS_CORTES` faz os cortes da demonstração andarem de 7 em 7 dias a partir de 10/11 às 18:00. Sem ela, valem o dia, a hora e o fuso do cliente.
- **Conferência em qualquer fechamento com rodada** (o antigo término, ADR 0012). A tela avisa quando um fechamento anterior ao atual tem pendência e não tem conferência na sua rodada mais recente. O aviso não cria estado de "semana fechada" (ADR 0003): ele só lê as conferências.

## Alternativas recusadas

- **Relógio simulado global, guardado no banco.** É ferramenta de teste: pede flag, e um usuário mudaria o que todos veem.
- **Corte no pedido da ingestão.** Reabre o #11 sem ganho: a ingestão sempre quer o fechamento atual.
- **Calcular na api.** Mais rápido de fazer, mas quebra o ADR 0004.
- **Corte do enunciado como semana extra na lista de segundas.** Duas semanas sobrepostas, com um dia de diferença, e os recebíveis de 10/11 mudando de semana conforme a escolha.
- **Mudar o dia de fechamento da Marina para terça.** O dia é dela.
- **Conferência só no fechamento atual.** O aviso de fechamento sem conferência não teria ação.

## Consequências

- O `SINKFI_CORTE_FIXO` sai. A demonstração abre no fechamento mais recente com dado; com os CSVs de hoje, 10/11.
- Um fechamento anterior pode mostrar dado velho depois de uma correção, até alguém pedir "Reprocessar". É o preço de mostrar o que se viu.
- A lista de fechamentos depende do dia de fechamento do cliente. Trocar esse dia não tem transição definida: as rodadas antigas ficariam em cortes que a configuração nova não gera.

## Testes que garantem

- `semanas_vao_da_primeira_liquidacao_prevista_ate_a_vigente`
- `semana_cujo_corte_nao_passou_fica_fora`
- `com_ancora_os_cortes_andam_de_sete_em_sete_dias`
- `fechamento_atual_e_o_mais_recente_com_recebivel_previsto_ou_credito`
- `voltar_a_uma_semana_ja_calculada_mostra_a_rodada_dela`
- `pedir_semana_enfileira_o_corte_daquela_semana`
- `aviso_mostra_fechamento_anterior_com_pendencia_e_sem_conferencia`
