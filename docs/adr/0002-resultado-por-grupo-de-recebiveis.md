# Resultado por grupo de recebíveis

Status: aceito, 16/11/2026

A regra devolve grupos de recebíveis, não um status por recebível. Cada grupo tem esperado, caiu, não caiu e próximo fechamento, e todo recebível esperado está em exatamente um grupo, inclusive os conciliados (grupo de um recebível só). Quando um crédito sem NSU serve para mais de um recebível, eles ficam juntos num grupo só, e a regra não escolhe qual foi pago.

## Contexto

O T-3000 é um crédito de 2.100,00 sem NSU, e dois recebíveis da Stone têm o mesmo líquido e a mesma data. Sem um identificador que viaje da adquirente até o extrato, qualquer escolha entre eles é inferência.

## Alternativa recusada

Um status por recebível. No empate, os 2.100,00 que não caíram não têm uma linha certa. Repetidos nas duas linhas, somam 4.200,00. Divididos, viram 1.050,00 em cada, o que é falso. Numa linha só, é um sorteio, e a lojista pode cobrar da Stone uma venda já paga.

## Consequências

- Os números do relatório são somas dos grupos. Com os CSVs de 10/11: 26.065,89 caiu + 7.707,33 não caiu + 5.640,00 próximo fechamento = 39.413,22 esperado.
- A adquirente vem do recebível, nunca da loja. Quando a mesma adquirente atende duas lojas e o crédito não diz de qual é, o grupo fica "entre lojas".
- Esse modelo também explica a parcela pelo NSU: um NSU repetido sem "n/m" e com várias parcelas vencidas candidatas vira um grupo, em vez da "menor parcela em aberto".
- Quando existir uma chave mais forte (relatório de pagamentos da adquirente, código de estabelecimento por loja, QR dinâmico no Pix), ela entra antes da chave fraca e o modelo não muda.

## Testes que garantem

- `empate_na_chave_fraca_gera_um_grupo_com_os_dois_recebiveis`
- `soma_dos_grupos_fecha_com_o_esperado` (contra os CSVs reais)
- `empate_entre_lojas_vai_para_a_linha_entre_lojas`
- `casamento_usa_a_adquirente_do_recebivel`
- `nsu_sem_parcela_com_varias_candidatas_gera_grupo_ambiguo`
