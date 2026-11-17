# Decisões

<!--
Esqueleto. Os headings seguem a seção "Entrega" do README.md.
Cada comentário traz a frase pronta do doc de notas e a seção do doc de onde ela sai.
A narrativa é do João: apague os comentários conforme escrever.
Doc de notas: https://claude.ai/artifact/2xR8wkeAzs3pctwa4QrUBm
-->

## Quem usa, e qual trabalho essa pessoa termina

<!-- Fonte no doc: "Leitura do enunciado". -->

## O que entrou e o que ficou de fora

<!--
Fontes no doc: "Ordem de construção", "Com mais tempo" e o "Não suporta" de "Dia do fechamento por cliente".
Fora por decisão: gráficos pedidos pelo suporte.
-->

## A regra de fechamento

<!--
Uma frase que a Marina consiga aplicar. Candidatas do doc:

- Corte: "O que caiu depois das 18:00 de segunda não está faltando: entra no fechamento seguinte."
- Severidade: "Falta de verdade é dinheiro que muda o fechamento: não entrou, ou entrou e não é seu. Dinheiro a mais que não é venda fica para conferir."
- Trava (ADR 0003): "O relatório não impede ninguém de fechar. Ele soma o que falta de verdade e, se a Marina definiu um limite, avisa quando a soma passa dele." Mais uma linha: no enunciado, "travar" significa recomendar não fechar, não bloquear.
- Princípio: "Quando os dados não decidem, a regra não adivinha: mostra a dúvida com o contexto mais específico que tiver."
- Grupos (ADR 0002): "Quando um crédito sem o código da venda serve para mais de uma venda, eu não escolho: mostro as vendas juntas e quanto falta no grupo."
- Janela da chave fraca: "Crédito sem NSU só casa por adquirente e valor se cair entre um dia antes e quatro dias depois da data prevista. Fora disso, aparece como pendência."
-->

## O que eu perguntaria para a Marina amanhã

<!-- Fonte no doc: "O que eu perguntaria". -->

## Desenho

<!--
Peças, o que cada uma faz, onde a regra mora, o que fica gravado, trade-off aceito.

- Fluxo (ADR 0004): "A ingestão grava o dado e o pedido de fechamento na mesma transação. Uma tarefa periódica publica os pedidos na fila, e o worker roda a regra e grava uma rodada que não muda mais."
- Rodada (ADR 0006; serve também a Debugar): "Cada rodada guarda uma cópia do que usou, e o hash inclui a versão da regra. Assim dá para explicar um número antigo exatamente como a Marina o viu, e uma correção na regra gera uma rodada nova em vez de devolver a errada."
- Limite: "O limite da trava é uma preferência da Marina, não um dado do fechamento. Ele fica fora da rodada e o resumo é calculado na leitura, então mudar o limite não recalcula nada. O que ela viu ao terminar fica gravado no 'Terminei'."
- Corte por cliente: "O fechamento da segunda é da Marina, não do sistema. A regra recebe o corte como parâmetro, cada cliente tem seu dia e hora, e um fechamento continua recebendo rodadas até o corte seguinte, para pegar o dado bancário que chega atrasado."
- Acesso: ADR 0005.
- Trade-off: o "Trade-off" de "Stack e plataforma" e o "Custo" de "O que a rodada grava" (dados duplicados a cada rodada).
-->

## Monitorar

<!--
- Término: "O sinal de que a Marina terminou é um botão 'Terminei' que só registra quem, quando e qual rodada ela viu. Se uma rodada nova muda o fechamento depois disso, a tela avisa o que mudou, e quem clica de novo na mesma semana é o primeiro sinal de que o número não convenceu."
- Falta: o sinal de que o fechamento rodou (rodada gravada por cliente e por corte, dead letter da fila).
-->

## Debugar

<!--
Caminho da frase dela até o recebível, o lançamento e a decisão da regra.
Fontes: a frase de Rodada em Desenho, a busca por recebível (índice GIN, ADR 0006) e a explicação de cada grupo na tela.
-->

## Responder

<!--
Sem frase pronta no doc. Material: rodada imutável e reprocessamento pelo suporte (ADR 0005), versão da regra no hash (ADR 0006), retry e dead letter (ADR 0004), aviso "mudou desde que você terminou".
-->

## Evoluir

<!--
- Banco: "O acesso ao banco é síncrono, na api e no worker, porque a api só faz consultas curtas sobre rodadas já calculadas e o trabalho pesado roda fora da requisição. Para atender mais gente, sobem mais cópias da api com um pool de conexões na frente do Postgres. Eu trocaria para assíncrono se a api passasse a esperar um serviço externo lento dentro da requisição, como consultar o Open Finance na hora; o sinal seria o tempo de resposta subir com as threads todas ocupadas e o banco ocioso."
- Chave mais forte (ADR 0002): relatório de pagamentos da adquirente, código de estabelecimento por loja, QR dinâmico no Pix.
- Fonte no doc: "Com mais tempo".
-->

## Como usei IA

<!-- Fonte no doc: "Como uso IA no desafio". Não é pedido pelo README; tirar se não couber. -->
