# Análise dos dados do fechamento de 10/11

Primeira leitura dos CSVs em `dados/`, feita antes de construir o produto, para entender o que os dados trazem e onde estão as armadilhas.

Esta leitura é **provisória**. Ela aplica a política do README com a regra de casamento descrita abaixo. Ainda não foram decididos a materialidade, o caso ambíguo do `T-3000`, o tratamento de dinheiro vindo de venda cancelada nem o tratamento de entradas sem recebível. Os números mudam conforme essas decisões.

Valores em reais (os CSVs estão em centavos). Horários em `America/Sao_Paulo`.

## Regra usada nesta leitura

1. Remove linhas repetidas do extrato pelo `transaction_id`.
2. Ignora tarifa da conta (`fee`) e transferência da própria titular (`internal_transfer`).
3. Casa cada recebível com um crédito em duas passadas:
   - **NSU na descrição**, desde que o crédito venha da adquirente certa (`settlement` com a contraparte da adquirente) ou seja `pix_in`, no caso de recebível Pix.
   - **Adquirente + valor líquido igual**, só para créditos cuja descrição não cita NSU nenhum e lançados a partir do dia da venda.
4. Crédito `pending` ou lançado depois das 18:00 de 10/11 vai para o próximo fechamento.
5. Chargeback desfaz o crédito original, mesmo quando é lançado depois das 18:00.
6. Parcela com `expected_settlement_at` depois de 10/11 fica como "a vencer".

## Indicadores

| Indicador | Valor |
| --- | ---: |
| Esperado até 10/11 (15 recebíveis, líquido) | R$ 39.413,22 |
| Bruto desses 15 recebíveis | R$ 39.982,50 |
| Entrou e conta neste fechamento | R$ 26.065,89 |
| **Falta de verdade** (4 recebíveis) | **R$ 7.707,33** |
| Fica para o próximo fechamento (2 créditos) | R$ 5.640,00 |
| MDR e antecipação (não é venda faltando) | R$ 569,28 |
| Entradas sem recebível (2 Pix de terceiros) | R$ 1.521,83 |
| Entrou de venda cancelada | R$ 3.152,00 |

Conferência: 26.065,89 + 7.707,33 + 5.640,00 = 39.413,22.

### Por loja

| Loja | Esperado | Entrou | Falta | Próximo fechamento |
| --- | ---: | ---: | ---: | ---: |
| Loja Centro (Stone) | R$ 31.163,97 | R$ 19.244,64 | R$ 6.919,33 | R$ 5.000,00 |
| Loja Savassi (PagSeguro) | R$ 8.249,25 | R$ 6.821,25 | R$ 788,00 | R$ 640,00 |

A Loja Centro concentra quase toda a falta. Só o pagamento parcial do `rec_7001` responde por 62% dela.

### O que compõe a falta

| Recebível | Situação | Falta | Motivo |
| --- | --- | ---: | --- |
| `rec_7001` | Parcial | R$ 4.775,00 | `T-7001` pagou R$ 10.000,00 de R$ 14.775,00 |
| `rec_3002` | Sem crédito (ambíguo) | R$ 2.100,00 | Só o `T-3000` serve para `rec_3001` e `rec_3002`, que são idênticos |
| `rec_5001` | Estornado | R$ 788,00 | O chargeback `T-5001R` (10/11 às 19:12) desfez o `T-5001` |
| `rec_1003` | Sem crédito | R$ 44,33 | Nenhum crédito da Stone. O `T-TRAP` tem o mesmo valor, mas vem de pessoa física |

## Recebíveis

| Recebível | Loja | Parcela | Previsto | Líquido | Entrou | Situação | Lançamento | Por quê |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| `rec_1001` | Centro | 1/1 | 05/11 | 1.477,50 | 1.477,50 | Conciliado | `T-1001` | 1.500,00 − 22,50 de taxas, por NSU |
| `rec_1002` | Centro | 1/1 | 06/11 | 877,14 | 877,14 | Conciliado | `T-1002` | Por adquirente + valor (descrição sem NSU) |
| `rec_1003` | Centro | 1/1 | 09/11 | 44,33 | 0,00 | Sem crédito | | Nenhum crédito da adquirente |
| `rec_4812` | Centro | 1/1 | 09/11 | 4.790,00 | 4.790,00 | Conciliado | `T-4812` | 4.812,00 − 22,00 de MDR: são os "R$ 22" da Marina |
| `rec_3001` | Centro | 1/1 | 09/11 | 2.100,00 | 2.100,00 | Conciliado | `T-3000` | Por adquirente + valor, mas o crédito também serviria para `rec_3002` |
| `rec_3002` | Centro | 1/1 | 09/11 | 2.100,00 | 0,00 | Sem crédito | | Ambíguo com `rec_3001` |
| `rec_2001` | Savassi | 1/1 | 07/11 | 3.152,00 | 3.152,00 | Conciliado | `T-2001` | Por NSU |
| `rec_2009` | Savassi | 1/1 | 06/11 | 3.152,00 | n/a | Cancelado | `T-2009` | Venda cancelada, mas o dinheiro entrou em 09/11 às 17:44 |
| `rec_6001a` | Savassi | 1/3 | 06/11 | 1.773,00 | 1.773,00 | Conciliado | `T-6001` | Por NSU |
| `rec_6001b` | Savassi | 2/3 | 04/12 | 1.773,00 | n/a | A vencer | | Fora deste fechamento |
| `rec_6001c` | Savassi | 3/3 | 04/01 | 1.773,00 | n/a | A vencer | | Fora deste fechamento |
| `rec_5001` | Savassi | 1/1 | 06/11 | 788,00 | 0,00 | Estornado | `T-5001` | Chargeback `T-5001R` |
| `rec_5002` | Savassi | 1/1 | 07/11 | 246,25 | 246,25 | Conciliado | `T-5002` | Por adquirente + valor (descrição sem NSU) |
| `rec_7001` | Centro | 1/1 | 10/11 | 14.775,00 | 10.000,00 | Parcial | `T-7001` | Faltam 4.775,00 |
| `rec_7002` | Savassi | 1/1 | 10/11 | 640,00 | 0,00 | Próximo fechamento | `T-7002` | Veio como `21:40Z`, que em São Paulo é 18:40, depois do corte |
| `rec_4002` | Centro | 1/1 | 10/11 | 5.000,00 | 0,00 | Próximo fechamento | `T-4002` | `pending`, lançado às 18:21 |
| `rec_8002` | Savassi | 1/1 | 09/11 | 450,00 | 450,00 | Conciliado | `T-8002` | 500,00 − 7,50 de MDR − 42,50 de antecipação |
| `rec_pix` | Savassi | 1/1 | 09/11 | 1.200,00 | 1.200,00 | Conciliado | `T-PIX` | Pix sem MDR. O pagador é o comprador, e o casamento é pela descrição `PIX-7001` |

## Extrato

| Linha | Transação | Horário (SP) | Valor | Leitura | Recebível | Por quê |
| --- | --- | --- | ---: | --- | --- | --- |
| `ext_01` | `T-1001` | 05/11 14:02 | 1.477,50 | Conciliado | `rec_1001` | |
| `ext_02` | `T-1001` | 05/11 14:02 | 1.477,50 | Duplicado | | O Open Finance sincronizou duas vezes |
| `ext_03` | `T-1002` | 06/11 15:11 | 877,14 | Conciliado | `rec_1002` | |
| `ext_04` | `T-4812` | 09/11 10:08 | 4.790,00 | Conciliado | `rec_4812` | |
| `ext_05` | `T-3000` | 09/11 13:15 | 2.100,00 | Conciliado | `rec_3001` | Ambíguo |
| `ext_06` | `T-2001` | 07/11 11:20 | 3.152,00 | Conciliado | `rec_2001` | |
| `ext_07` | `T-2009` | 09/11 17:44 | 3.152,00 | Venda cancelada | `rec_2009` | Dinheiro a mais. A adquirente deve cobrar de volta |
| `ext_08` | `T-6001` | 06/11 11:47 | 1.773,00 | Conciliado | `rec_6001a` | |
| `ext_09` | `T-5001` | 06/11 12:30 | 788,00 | Estornado | `rec_5001` | |
| `ext_10` | `T-5001R` | 10/11 19:12 | 788,00 | Estorno | `rec_5001` | Depois do corte, mas conta porque o crédito original é deste fechamento |
| `ext_11` | `T-5002` | 07/11 09:40 | 246,25 | Conciliado | `rec_5002` | |
| `ext_12` | `T-7001` | 10/11 14:55 | 10.000,00 | Parcial | `rec_7001` | |
| `ext_13` | `T-7002` | 10/11 18:40 | 640,00 | Fora do corte | `rec_7002` | O horário original estava em UTC |
| `ext_14` | `T-4002` | 10/11 18:21 | 5.000,00 | Fora do corte | `rec_4002` | `pending` |
| `ext_15` | `T-8002` | 09/11 11:51 | 450,00 | Conciliado | `rec_8002` | |
| `ext_16` | `T-PIX` | 09/11 08:16 | 1.200,00 | Conciliado | `rec_pix` | |
| `ext_17` | `T-FEE` | 10/11 23:59 | 3,50 | Fora do escopo | | Tarifa da conta |
| `ext_18` | `T-INT` | 10/11 09:00 | 5.000,00 | Fora do escopo | | Transferência da própria titular |
| `ext_19` | `T-TRAP` | 09/11 16:40 | 44,33 | Não identificado | | Mesmo valor de `rec_1003`, mas o pagador é pessoa física |
| `ext_20` | `T-XREF` | 09/11 17:05 | 1.477,50 | Não identificado | | Cita `STN-1001`, mas o pagador é a Comercial Atlas e `rec_1001` já casou |

## O que esperar dos dados

- **18 recebíveis:** 15 vencem até 10/11, 2 são parcelas futuras e 1 está cancelado. Em todos vale líquido = bruto − MDR − antecipação. A falta deve ser calculada sobre o líquido, nunca sobre o bruto.
- **20 linhas de extrato:** 1 duplicata, 2 fora do escopo e 1 com horário em UTC. Só 15 delas são créditos que contam para algum recebível.
- **A descrição nem sempre traz o NSU** ("vendas stone novembro", "pagseguro loja", "stone"). Sem ele, o casamento depende de adquirente e valor, e isso gera empate quando há dois recebíveis iguais.
- **No Pix, o pagador é o comprador**, não a adquirente. Pix de terceiros pode ter o mesmo valor de um recebível, ou citar o mesmo NSU, sem ser ele. Casar só por valor ou só por texto erra.
- **O único horário em UTC está na fronteira do corte.** Sem conversão para São Paulo, o `T-7002` entraria no fechamento errado e ninguém perceberia.

## Decisões em aberto

- **Materialidade:** a partir de qual diferença o fechamento trava?
- **`T-3000`:** casar com um dos dois recebíveis idênticos, ou marcar os dois como ambíguos para revisão manual?
- **Venda cancelada que recebeu dinheiro (`T-2009`):** trava o fechamento ou só gera aviso?
- **Entradas sem recebível (`T-TRAP`, `T-XREF`):** como mostrar dinheiro que entrou mas não é venda das lojas?
- **Créditos fora do corte (`rec_7002`, `rec_4002`):** confirmar com a Marina que "próximo fechamento" faz sentido para ela, em vez de "faltando".
