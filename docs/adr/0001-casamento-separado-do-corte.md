# Casamento separado do corte

Status: aceito, 16/11/2026

O fechamento responde três perguntas diferentes: este crédito paga qual recebível (casamento), ele conta neste fechamento (corte) e o que a lojista vê para cada grupo (leitura). Decidimos responder cada uma numa etapa própria, nesta ordem: normalizar, casar, aplicar o corte e o chargeback, classificar. O casamento não leva o corte em conta.

## Alternativa recusada

Descartar no casamento os créditos lançados depois do corte. O T-7002 (640,00) caiu às 18:40 de São Paulo, lançado como 21:40Z. Com o corte aplicado antes, ele vira duas linhas falsas: "não caiu 640,00" no rec_7002 e "entrada sem recebível 640,00". Casando primeiro, vira um item só, no próximo fechamento.

## Consequências

- O "próximo fechamento" só existe porque o crédito casou antes de ser cortado. Ele fica fora das pendências e da trava.
- A normalização roda antes de tudo: converte horários para São Paulo, junta lançamentos repetidos pela transação e tira tarifa e transferência da própria titular. Um horário em UTC perto do corte só fica certo se for convertido antes de cortar.
- Cada etapa pode ser testada sozinha, com dados pequenos.

## Testes que garantem

- `credito_depois_do_corte_vai_para_proximo_fechamento`
- `duplicata_nao_vira_pendencia`
