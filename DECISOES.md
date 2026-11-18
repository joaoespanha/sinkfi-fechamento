# Decisões

<!--
Esqueleto. Os headings seguem a seção "Entrega" do README.md.
Cada comentário traz a frase pronta do doc de notas e a seção do doc de onde ela sai.
A narrativa é do João: apague os comentários conforme escrever.
Doc de notas: https://claude.ai/artifact/2xR8wkeAzs3pctwa4QrUBm
-->

## Quem usa, e qual trabalho essa pessoa termina

Quem usa é a dona ou o dono de uma pequena empresa que faz o próprio fechamento. Vende por mais de uma adquirente e recebe tudo numa conta só. Não sabe o que é MDR, mas sabe quanto tinha que cair. Contratou a sinkfi para parar de conferir o extrato linha a linha. O trabalho que termina é o fechamento do período: saber o que pode fechar e o que está faltando de verdade. A Marina é o exemplo do enunciado: duas lojas, Stone e PagSeguro liquidando na mesma conta do Inter, fechamento toda segunda à noite.

O suporte pediu um dashboard de divergências com gráficos, e eu li o pedido como sintoma. O Rafa conta que quem fica reabrindo a tela de divergência cancela, e um cliente voltou para a planilha porque "pelo menos lá eu entendo". Listar melhor o que não bate não resolve isso; o que resolve é dizer o que cada coisa significa e o que fazer com ela. Por isso a tela abre com a resposta, "posso fechar?" e "o que falta de verdade?", e logo abaixo vêm as pendências, separadas em falta de verdade e para conferir. Cada pendência tem uma página própria: por que a regra a marcou, a linha do tempo da venda até o corte, o recebível e o crédito envolvidos, e o próximo passo provável, como conferir a liquidação no portal da adquirente, pedir o detalhamento de um repasse ou abrir um chamado com o NSU e a data prevista. A pendência deixa de ser uma linha vermelha e vira uma tarefa.

O suporte também usa o produto, para atender um chamado: abre o fechamento de qualquer cliente, vê o mesmo relatório que a lojista viu e pode pedir um reprocessamento. Não muda o limite da trava nem marca "Terminei" no lugar dela (ADR 0005).

## O que entrou e o que ficou de fora

**Entrou** o fechamento inteiro, do jeito que a lojista usa: ela abre a tela e vê se pode fechar e quanto falta de verdade, a semana dia a dia, as pendências separadas por severidade, o motivo e o próximo passo de cada uma. Define o próprio limite da trava, volta a fechamentos anteriores e marca "Terminei" quando acaba. Por baixo está o caminho de uma aplicação real, que sobe com `docker compose up`: ingestão, fila, rodadas que não mudam depois de gravadas e login com papéis separados para lojista e suporte.

**Ficou de fora, por decisão**, o que atrapalha o trabalho dela:

- A página de dashboard antes do fechamento: seria um clique a mais. Os gráficos pedidos pelo suporte entraram, mas dentro do fechamento.
- Um botão que tranca o período: o relatório informa, quem decide é ela (ADR 0003).

**Com mais tempo**, entraria:

- O webhook `recebivel.liquidado`, para o ERP do cliente dar baixa sozinho no que casou certo (ADR 0008, issue #30).
- O bloqueio progressivo da conta depois de tentativas de login erradas.
- A evolução semana a semana.
- O fechamento mensal ou quinzenal.

## A regra de fechamento

> O que estava previsto para cair até o dia do fechamento e foi confirmado na conta até as 18:00 está fechado; o que caiu depois entra no fechamento seguinte; e só é falta de verdade o dinheiro que não entrou, ou que entrou e não é seu.

- Dinheiro a mais que não é de venda, como um Pix de terceiro, fica **para conferir**: vale olhar, mas não muda o fechamento.
- Quando um crédito sem o código da venda serve para mais de uma venda, a regra não escolhe: mostra as vendas juntas e quanto falta no grupo (ADR 0002).
- O relatório informa, não bloqueia. Quem fecha é a lojista, e ela sabe coisas que os dados ainda não mostram: pode ter resolvido uma pendência com a adquirente e não precisa esperar o próximo lote para fechar. Bloquear também exigiria uma política de materialidade que ninguém definiu, e inventá-la seria decidir por ela. Por isso a trava é opcional: ela define um limite, e o resumo recomenda não fechar quando a soma das faltas de verdade passa dele (ADR 0003).

## O que eu perguntaria para a Marina amanhã

1. **Depois que a tela diz "pode fechar", o que você ainda confere na mão?** Se ela ainda abre o extrato, a aposta não pagou, e a resposta mostra o que falta.
2. **Das pendências da semana, quais você resolveu sozinha com o próximo passo da tela, e quais virariam chamado?** Diz se a pendência virou tarefa ou continua sendo uma linha vermelha.
3. **A partir de qual diferença você não fecharia?** Ninguém definiu essa materialidade, e a trava vem desligada. A resposta dela é o primeiro valor padrão para quem nunca mexeu no limite.
4. **Para onde vai o fechamento depois que você termina: planilha, contador, sistema da loja?** Se alguém ainda redigita o que casou, o próximo passo é o webhook para o ERP (ADR 0008), não mais uma tela.
5. **Quanto tempo levava o fechamento de segunda antes, e quanto levou com a tela?** É a medida mais direta de que o trabalho ficou menor, e a base do sinal em Monitorar.
6. **Quando a tela diz "falta de verdade", "para conferir" e "próximo fechamento", o que você entende por cada um?** São nomes que nós escolhemos. Se ela lê algum de outro jeito, a tela informa errado mesmo com o número certo, e foi por não entender que um cliente voltou para a planilha.

## Desenho

**Peças.** Seis serviços no Docker Compose: `web` (React) mostra o fechamento; `api` (FastAPI) faz o login, lê as rodadas e grava o limite, o "Terminei" e o pedido de reprocessamento; `beat` dispara a ingestão de cada cliente a cada 6 horas; `worker` (Celery) roda a regra; RabbitMQ entrega os pedidos; Postgres guarda tudo. A ingestão grava o dado e o pedido de fechamento na mesma transação. Uma tarefa periódica publica os pedidos na fila, e o worker roda a regra e grava uma rodada que não muda mais (ADR 0004). Se a publicação falha, o dado não fica no banco sem o pedido de recalcular. Na dead letter, `fechamento.morta`, só cai o que falhou de verdade: o pedido repetido devolve a rodada que já existe, por causa de uma trava por cliente, e a tarefa que trava ou derruba o processo termina ali em vez de voltar sem fim.

**Onde a regra mora.** Em `backend/src/fechamento/`, como funções puras: `fechar(recebíveis, lançamentos, lojas, corte)` devolve os grupos e as pendências, e `resumo(pendências, limite)` devolve a recomendação. Não leem banco, fila, relógio nem arquivo, então são testadas em milissegundos, inclusive contra os CSVs reais. Em volta fica uma casca que carrega a entrada, chama a regra e grava o resultado; a casca depende do núcleo, nunca o contrário. O corte é entrada da regra: cada cliente tem seu dia e hora, e um fechamento continua recebendo rodadas até o corte seguinte, para pegar o crédito que o banco entregou atrasado.

**O que fica gravado.** Recebíveis e lançamentos ficam em tabelas que a ingestão atualiza, com as duplicatas do Open Finance, porque juntar é trabalho da regra. Cada rodada guarda uma cópia do que cada item usou, e o hash cobre a entrada, o corte e a versão da regra. Assim dá para explicar um número antigo exatamente como a lojista o viu, e uma correção na regra gera uma rodada nova em vez de devolver a errada (ADR 0006). O limite da trava é preferência dela, não dado do fechamento: fica fora da rodada. O "Terminei" grava quem, quando, qual rodada, o limite e o resumo daquele momento.

**Trade-offs que aceitei.**

- *Mais peças do que o problema pede.* Um fechamento é um cálculo de milissegundos por cliente por semana; a regra chamada pela rota bastaria. A fila e o outbox entraram pelas garantias de produção (retry, dead letter, trabalho fora da requisição), ao custo de seis serviços para subir e entender. O plano de corte é chamar a mesma função de forma síncrona.
- *Dados duplicados a cada rodada.* É o preço de a rodada antiga nunca mudar. O modelo mais limpo, versionar recebíveis e lançamentos, custava meio dia na ingestão.
- *Dois serviços, um contrato.* Os tipos do `web` são gerados do OpenAPI da `api`, e a CI falha se divergirem.

**Limites conhecidos da regra.**

- Crédito sem NSU só casa por adquirente e valor se cair entre um dia antes e quatro dias depois da data prevista. Fora disso, vira pendência.
- Na chave fraca, empates em que os candidatos só se sobrepõem em parte continuam resolvidos de forma gulosa.
- Um chargeback lançado depois do corte seguinte não volta ao fechamento do crédito que desfez.
- Um crédito sem venda que cai depois das 18:00 entra como "para conferir" neste fechamento, não no próximo.

## Monitorar

**O fechamento rodou.** Toda ingestão deixa um pedido de fechamento no Postgres, e todo pedido deve virar uma rodada para aquele cliente e corte. Observo três coisas: pedidos parados sem publicar, sinal de que a publicação ou o RabbitMQ parou; um cliente com ingestão nova e sem rodada nova para o fechamento vigente; e, principalmente, uma mensagem em `fechamento.morta`. Essa é o alarme: um fechamento que não rodou e só volta na próxima ingestão, até 6 horas depois. Como só cai ali o que falhou de verdade (ver Desenho), uma mensagem na dead letter nunca é ruído.

**Ela terminou.** O botão "Terminei" registra quem, quando e qual rodada ela viu, sem travar nada. Toda terça de manhã olho três números: quantos clientes terminaram, quantos terminaram sobre uma rodada que depois mudou e quem clicou mais de uma vez na mesma semana.

**O que muda antes do chamado.** O chamado começa quando o número não convence, e isso aparece antes no uso: ela clica "Terminei" de novo na mesma semana; uma rodada nova muda um fechamento que ela já tinha terminado (o crédito de sexta que só aparece no domingo), e a tela avisa o que mudou, mas só quando ela abre; um fechamento anterior fica com pendência e sem "Terminei", e a tela lembra na semana seguinte. Nos três casos, o suporte pode olhar antes de ela escrever.

**O que falta.** Hoje esses sinais são consultas nas tabelas. Com mais tempo, ligaria um alerta na dead letter e um painel com as contagens de terça, e gravaria quantas vezes ela abre a mesma pendência. O Rafa disse que quem fica reabrindo a tela cancela, e esse é o único sinal que ainda não registramos.

## Debugar

<!--
Caminho da frase dela até o recebível, o lançamento e a decisão da regra.
Fontes: a frase de Rodada em Desenho, a busca por recebível (índice GIN, ADR 0006) e a explicação de cada grupo na tela.
-->

## Responder

<!--
Sem frase pronta no doc. Material: rodada imutável e reprocessamento pelo suporte (ADR 0005), versão da regra no hash (ADR 0006), retry e dead letter (ADR 0004), aviso "mudou desde que você terminou".
Da revisão da fila (ADR 0004): o relay só marca o pedido como publicado depois que o RabbitMQ confirma; o retry aguenta ~13 min de Postgres fora, e uma queda maior manda o pedido para a dead letter, e o fechamento só volta na ingestão seguinte, até 6h depois; reiniciar o `beat` não adia a ingestão, que segue o relógio (0, 6, 12 e 18h UTC).
Como o cliente fica sabendo fora da tela: o webhook `recebivel.liquidado` (ADR 0008, proposto) é o canal para o ERP do cliente enterprise; hoje a Marina só sabe abrindo o fechamento.
-->

## Evoluir

<!--
- Banco: "O acesso ao banco é síncrono, na api e no worker, porque a api só faz consultas curtas sobre rodadas já calculadas e o trabalho pesado roda fora da requisição. Para atender mais gente, sobem mais cópias da api com um pool de conexões na frente do Postgres. Eu trocaria para assíncrono se a api passasse a esperar um serviço externo lento dentro da requisição, como consultar o Open Finance na hora; o sinal seria o tempo de resposta subir com as threads todas ocupadas e o banco ocioso."
- Chave mais forte (ADR 0002): relatório de pagamentos da adquirente, código de estabelecimento por loja, QR dinâmico no Pix. Perguntas às adquirentes: a Stone e o PagSeguro mandam relatório de pagamentos com as vendas de cada repasse? Cada loja tem código de estabelecimento próprio? Na antecipação, a agenda atualiza a data prevista?
- Webhook enterprise `recebivel.liquidado` (ADR 0008, proposto; issue #30): o ERP do cliente dá baixa sozinho no recebível que casou certo. Evento no outbox na transação da rodada, retry no Postgres, assinatura Standard Webhooks, SSRF conferido a cada envio. Ficou de fora porque não serve ao trabalho da Marina, que é fechar a semana; entra se aparecer cliente com ERP pedindo integração.
- Fonte no doc: "Com mais tempo".
-->

## Como usei IA

<!-- Fonte no doc: "Como uso IA no desafio". Não é pedido pelo README; tirar se não couber. -->
