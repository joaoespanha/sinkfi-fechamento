# Debugar: "o número não bate"

O caminho da frase da lojista até o recebível, o lançamento e a decisão da regra, para quem está de plantão sem quem escreveu o código. Os termos (rodada, corte, chave forte e fraca, grupo, versão da regra) estão no `GLOSSARY.md`.

Os exemplos usam a demonstração: `docker compose up`, a tela em `http://localhost:8080` (ou o `WEB_PORT`) e a cliente `cli_marina`.

## 1. Qual rodada ela viu

Entre como suporte (`suporte@sinkfi.demo`), procure a cliente pelo e-mail da lojista, pelo CNPJ ou pelo nome, que é o que chega no chamado (ADR 0010), e abra o fechamento dela. O aviso da conferência diz quem conferiu, quando e sobre qual rodada.

- **Mesma rodada da tela:** ela viu o que você está vendo. Siga para o passo 2.
- **"O fechamento mudou desde a última conferência":** a tela mostra o resumo de antes e o de agora. A primeira pergunta é se a diferença vem dessa mudança, como um crédito que chegou depois da conferência. Para ver os itens da rodada antiga, use o passo 3.

## 2. Qual item

Abra a pendência que ela cita. A página do item mostra o motivo, ou a chave pela qual casou, a linha do tempo da venda até o corte, o próximo passo sugerido, e os recebíveis e créditos com NSU, valores e datas. Anote o NSU.

## 3. Em quais rodadas a venda aparece e o que a regra viu em cada uma

Com o login de suporte no mesmo navegador, abra `http://localhost:8080/api/docs`:

- `GET /clientes/{cliente_id}/rodadas?nsu=STN-1002` lista as rodadas em que a venda aparece, da mais nova para a mais antiga, com a versão da regra e o corte de cada uma. Sem `nsu`, lista todas as rodadas do cliente.
- `GET /clientes/{cliente_id}/rodadas/{rodada_id}` devolve a rodada pedida no mesmo formato do fechamento, inclusive quando ela já não é a mais recente.

Cada item traz a **cópia** do recebível e do lançamento que a regra usou naquela rodada (ADR 0006). Se o dado mudou no banco depois, a cópia continua mostrando o que a regra recebeu.

## 4. A regra de hoje decide igual

```sh
docker compose exec api python -m sinkfi.reproduzir cli_marina <rodada_id>
```

O script só lê. Ele responde três perguntas:

- **Versão da regra.** Se a rodada é de uma versão anterior, uma correção na regra pode explicar a diferença. Uma correção gera rodada nova, e nunca muda a antiga.
- **Entrada.** Recalcula o hash com o dado de hoje e o corte e a versão da rodada. Se não bate, lista o que mudou ou sumiu da cópia gravada. Exemplo: se a rodada gravou o `ext_14` como `confirmed` e o extrato de hoje o traz `pending`, a lista mostra a troca, e o lançamento passa para o próximo fechamento. Lista vazia com entrada mudada quer dizer que entrou dado novo. O lançamento aparece pelo id (`ext_14`); o recebível, pelo id com a adquirente (`rec_1002 (stone)`), porque duas adquirentes podem usar o mesmo id (ADR 0009).
- **Decisão.** Com a mesma entrada, roda a regra de hoje e compara item a item com o gravado. Uma diferença ali é regressão ou correção da regra, e vira issue.

## 5. Por que a regra decidiu assim

A regra fica em `backend/src/fechamento/`, como funções puras. O motivo de cada pendência está no `GLOSSARY.md`, e os grupos e a chave fraca, na ADR 0002. Para isolar um caso, monte um teste em `backend/tests/` com os construtores de `tests/construtores.py` (`recebivel`, `lancamento`, `CORTE`), copiando os valores do passo 3. Ele roda em milissegundos, sem banco nem fila, e fica como teste de regressão.

## 6. O fechamento não rodou

- Primeiro, se a aplicação está de pé: `docker compose ps` mostra `healthy` ou `unhealthy` em api, web e worker, e `/api/health` (sem login) diz se a api fala com o Postgres e com o broker. Um 503 nomeia o que caiu. O beat não tem health check: a morte dele aparece pela ingestão, abaixo (ADR 0013).
- `GET /operacao` (só o suporte, pelo mesmo `/api/docs`) mostra a saúde da fila:
  - `pedidos_pendentes` e `idade_do_mais_antigo_segundos`: ingestões gravadas que o relay do outbox ainda não publicou. O relay roda a cada 10 segundos; um pedido pendente há minutos quer dizer beat ou worker fora do ar.
  - `mensagens_na_dead_letter`: ingestões e fechamentos que falharam de vez, na fila `fechamento.morta`. `null` quer dizer que a api não alcançou o RabbitMQ, ou que ele recusou o login.
  - `ultima_ingestao_em`: a ingestão mais recente de qualquer cliente. A agenda é 0, 6, 12 e 18h UTC; mais de 6 horas atrás é uma execução perdida.
  - `clientes_com_ingestao_atrasada`: os clientes sem ingestão há mais de 12 horas, a mesma regra do "atrasada" que a lojista vê na tela (ADR 0011). Cliente que nunca teve ingestão não entra.
- `docker compose logs worker | grep "dead letter"` mostra cada falha definitiva com a tarefa, o que ela recebeu (cliente e, quando houver, corte) e o erro. Também sai a linha do processo que morreu (falta de memória, por exemplo) depois de acabarem as tentativas. As mensagens ficam no painel do RabbitMQ (`http://localhost:15672`). Como volta depende da tarefa:
  - `ingerir_cliente` e `fechar_cliente`: na próxima ingestão, até 6 horas depois.
  - `fechar_semana` e `reprocessar_cliente`: a ingestão só pede o fechamento atual, então o corte antigo só volta com um reprocessamento pelo suporte (ADR 0004).
- `docker compose logs worker | grep "limite duro"` mostra a tarefa que passou de 150 segundos e foi morta. Ela recebeu ack e **não** está na fila morta nem na contagem da `/operacao`: volta do mesmo jeito que a dead letter, pela tabela acima.
- `docker compose logs worker | grep "rodada "` mostra cada rodada com cliente, corte, versão e se é **nova** ou **existente**. Existente quer dizer que a entrada é igual à de uma rodada que já existe, e o pedido devolveu essa rodada.

### O beat parou

O beat agenda a ingestão e o relay do outbox. Sem ele, nenhum pedido novo entra no outbox, e `pedidos_pendentes` e `mensagens_na_dead_letter` ficam em zero: a fila parece saudável. O sinal é a ingestão:

- **Todos os clientes atrasados, ou `ultima_ingestao_em` velha:** o beat (ou o worker) parou. Veja `docker compose ps beat worker` e `docker compose logs beat`. Depois de subir de novo, a próxima hora da agenda cobre; não há ingestões acumuladas.
- **Um cliente atrasado e os outros em dia:** o problema é do cliente. Procure `cli_<id>` em `docker compose logs worker`: falta a pasta de dados, ou a ingestão dele foi para a dead letter.

### A tela ou o `/api/docs` responde 502

O nginx resolve o nome da api pelo DNS do Docker a cada 10 segundos, então o 502 logo depois de recriar a api passa sozinho. Se ele continuar, a api não está respondendo: veja `docker compose ps api` e `docker compose logs api`.
