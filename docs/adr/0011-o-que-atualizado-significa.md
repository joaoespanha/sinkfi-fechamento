# O que "atualizado" significa para a lojista: a última ingestão, não a rodada

Status: aceito, 18/11/2026

O cartão de resumo ganha uma linha própria, abaixo do "Corte em": "Dados atualizados em 18/11, 15:00 · próxima atualização prevista às 21:00". A lojista e o suporte veem a mesma linha. A hora da atualização vem da última ingestão que deu certo, gravada em `clientes.ultima_ingestao_em`. A próxima é calculada pela agenda da ingestão. Escolhemos assim porque a lojista precisa saber até quando os números valem, e a hora da rodada não responde isso.

## Contexto

A ingestão roda pelo relógio às 0, 6, 12 e 18h UTC (21h, 3h, 9h e 15h em São Paulo). A execução que vence com o worker fora não roda, e a seguinte cobre.

A rodada já tem `criada_em`, mas a ingestão sem dado novo devolve a rodada que já existe (o hash do ADR 0006). Mostrar a hora da rodada diria "parado desde ontem" sobre dados que o sistema conferiu há pouco.

A hora da última ingestão não era gravada em lugar nenhum. O `criado_em` do pedido no outbox (ADR 0004) chegava perto, mas pertence à infraestrutura.

## Decisões

- **"Atualizado" é a última ingestão que deu certo** (GLOSSARY: Atualização), com ou sem dado novo. A hora entra na transação do dado: uma ingestão desfeita não conta.
- **Uma coluna no cliente**, `ultima_ingestao_em`, com a hora do banco, como o pedido do outbox. A migração preenche os clientes antigos com o pedido mais recente do outbox.
- **A agenda mora num lugar só.** `HORAS_DA_INGESTAO` (`sinkfi.atualizacao`) alimenta o beat e a leitura. A próxima hora é a primeira da agenda estritamente depois de agora: na hora exata, a próxima é a seguinte.
- **"Prevista", não "às".** O texto não promete a próxima, porque uma execução perdida é coberta pela seguinte.
- **Atrasada depois de 12 h (dois ciclos).** Um ciclo perdido pode ser só o worker fora. Com dois, os números podem estar velhos: a linha ganha o tom de atenção e nomeia a primeira atualização que não aconteceu ("a atualização prevista para 17/11 às 21:00 não aconteceu"). Quem decide é o backend, com o relógio injetado da api: o texto não depende do relógio do navegador.
- **Sem ingestão, a linha diz isso:** "Ainda sem atualização · primeira prevista …". Ela não some.
- **Hora absoluta e curta, no fuso de São Paulo.** A próxima mostra só a hora quando cai no mesmo dia da última, e o dia junto quando não cai. A comparação é com a última, não com o relógio da tela.
- **A resposta do fechamento leva a atualização do cliente agora**, também quando o suporte abre uma rodada antiga (Debugar).

## Alternativas recusadas

- **A hora da rodada.** Ela fica parada quando a ingestão não traz dado novo (ADR 0006).
- **O `max(criado_em)` do outbox, sem migração.** Funciona hoje, mas pega emprestado um detalhe da infraestrutura: a limpeza do outbox ou um pedido criado por outro caminho mudaria o que a lojista lê.
- **Hora relativa ("há 2 horas").** Pede um relógio na tela e é mais difícil de testar. A hora absoluta casa com o "Corte em".
- **Calcular a próxima no web.** A agenda ficaria em dois lugares e mudaria em um só.

## Consequências

- **Uma hora para todas as fontes.** Hoje adquirentes e Open Finance chegam juntos, numa pasta por cliente. Com integração real, cada fonte terá a sua hora e a linha terá que dizer qual está velha.
- **Agenda por cliente.** Se a agenda passar a variar por cliente, `HORAS_DA_INGESTAO` vira configuração do cliente, como o corte.
- **O tom pisca por segundos.** Na hora exata do segundo ciclo, os dados contam como atrasados até a ingestão em curso gravar. Aceitamos.

## Testes que garantem

- `antes_de_uma_hora_da_agenda_a_proxima_e_ela`, `em_cima_da_hora_da_agenda_a_proxima_e_a_seguinte`, `depois_da_ultima_do_dia_a_proxima_e_no_dia_seguinte`
- `doze_horas_ainda_nao_e_atraso`, `mais_de_doze_horas_esta_atrasada_e_nomeia_a_primeira_perdida`, `sem_ingestao_mostra_so_a_proxima`
- `ingestao_grava_a_hora_da_ultima_ingestao`, `ingestao_desfeita_nao_conta_como_atualizacao`
- `fechamento_devolve_a_ultima_ingestao_e_a_proxima_prevista`
- web: `linha da atualização` (mesmo dia, dia seguinte, atrasada, sem ingestão)
