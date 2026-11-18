# Lotes de teste

`python dados-teste/gerar.py` gera `lote1/` e `lote2/`. Cada um é a pasta `dados/` inteira: a base
do repositório mais as linhas novas. O lote 2 contém o lote 1.
O script lê a base do último commit (`git show HEAD:dados/...`), então roda certo mesmo com um lote
já copiado por cima de `dados/`.

Para aplicar um lote, copie os três arquivos por cima de `dados/` e dispare a ingestão:

```powershell
Copy-Item dados-teste\lote1\*.csv dados\ -Force
docker compose exec worker celery -A sinkfi.tarefas call sinkfi.agendar_ingestoes
```

Não abra nem salve os CSVs no Excel: ele grava BOM e `;`, e a ingestão cai na dead letter.

Para voltar à base: `git checkout -- dados`, `docker compose down -v` e `docker compose up --build -d`.
Só o checkout não basta, porque a ingestão atualiza pelo id e não apaga.

## Semanas

O corte é toda terça às 18:00 de Brasília.

| Fechamento | Dias | De onde vêm os dados |
|---|---|---|
| 03/11 | 28/10 a 03/11 | lote 1: `rec_31xx` / `ext_31`, `ext_32` |
| 10/11 | 04/11 a 10/11 | a base do repositório |
| 17/11 | 11/11 a 17/11 | lote 1: `rec_17xx` / `ext_41` a `ext_54` |

## Casos

| Caso | NSU | Lote 1 | Lote 2 |
|---|---|---|---|
| Casa pelo NSU | STN-3101 | ok | ok |
| Casa sem NSU (chave fraca) | PAG-3102 | ok | ok |
| Não caiu | STN-3103 | não caiu, R$ 2.300,00 | chega em 12/11 e casa |
| Casa pelo NSU, com linha repetida no extrato | STN-1701 | ok (ext_41b some na normalização) | ok |
| Casa sem NSU (chave fraca) | PAG-1702 | ok | ok |
| Não caiu | STN-1703 | não caiu, R$ 3.129,00 | continua |
| Caiu em parte | PAG-1704 | caiu em parte, R$ 1.000,00 | o resto cai em 18/11, depois do corte, e vai para o próximo fechamento |
| Caiu a mais | STN-1705 | caiu a mais, R$ 100,00 | continua |
| Crédito pending | STN-1706 | próximo fechamento, R$ 4.200,00 | confirma às 17:30 de 17/11 e casa |
| Pix | PIX-1707 | ok | ok |
| Caiu depois do corte (17/11 19:30) | PAG-1708 | próximo fechamento, R$ 543,20 | continua |
| Chargeback | PAG-1709 | ok | chargeback, R$ 1.280,00 |
| Pix de pessoa física, sem venda | ext_50 | para conferir, R$ 250,00 | continua |
| Parcela 2/2 adiantada | PAG-1710 | 1/2 ok; 2/2 pode ser antecipação, R$ 900,00 | continua |
| Venda cancelada que caiu | STN-1711 | venda cancelada, R$ 394,00 | continua |
| Tarifa | ext_54 | ignorada | ignorada |
| Pending de 10/11 | STN-4002 (ext_14) | próximo fechamento | confirma em 11/11 e casa |

## Esperado pela regra (versão 3)

| Lote | Fechamento | Falta de verdade | Para conferir |
|---|---|---|---|
| base | 10/11 | R$ 10.859,33 em 5 | 2 |
| 1 | 17/11 | R$ 17.782,33 em 10 | 4 |
| 1 | 10/11 (se reprocessar) | R$ 13.159,33 em 6 | 2 |
| 1 | 03/11 | R$ 2.300,00 em 1 (STN-3103) | 0 |
| 2 | 17/11 | R$ 15.762,33 em 9 | 4 |
| 2 | 10/11 (se reprocessar) | R$ 10.859,33 em 5 | 2 |
| 2 | 03/11 | R$ 0,00 | 0 |

O fechamento de 17/11 acumula: ele inclui as pendências de 10/11 que ainda não se resolveram.

O crédito que não paga recebível esperado (entrada sem recebível, pode ser antecipação, venda
cancelada) entra no fechamento em que cair: confirmado até o corte. Por isso o ext_53 (STN-1711,
14/11) só aparece em 17/11. O `backend/tests/test_lotes_de_teste.py` confere esta tabela.
